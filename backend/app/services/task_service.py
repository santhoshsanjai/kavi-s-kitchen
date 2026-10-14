import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.meal_windows import MealWindow
from app.domain.task_states import TERMINAL, TaskStatus, assignment_expired
from app.models.customer import Customer
from app.models.delivery import (
    AssignmentStatus, DeliveryTask, DeliveryTrip, DriverAssignment, TaskType, TripStatus,
)
from app.models.one_time_order import OneTimeOrder, OneTimeOrderLine, OneTimeOrderStatus
from app.models.subscription import SlotStatus, Subscription, SubscriptionMealSlot, SubscriptionStatus
from app.models.user import User
from app.schemas.user import UserRole
from app.services.common import alert, audit, lock, move_task, require_reason
from app.services.errors import Conflict, NotFound, ValidationFailed
from app.services.settings_service import get_settings


async def generate_tasks(db: AsyncSession, service_date: date) -> int:
    """
    Creates delivery tasks for every scheduled subscription meal and confirmed one-time order line
    on a date. Safe to run repeatedly: partial unique indexes allow one live task per source.
    """
    created = 0
    slot_rows = (await db.execute(
        select(SubscriptionMealSlot, Subscription.customer_id, Customer.address)
        .join(Subscription, Subscription.id == SubscriptionMealSlot.subscription_id)
        .join(Customer, Customer.id == Subscription.customer_id)
        .where(SubscriptionMealSlot.service_date == service_date,
               SubscriptionMealSlot.status == SlotStatus.SCHEDULED,
               Subscription.status == SubscriptionStatus.ACTIVE)
    )).all()
    for slot, customer_id, address in slot_rows:
        res = await db.execute(insert(DeliveryTask).values(
            id=uuid.uuid4(), task_type=TaskType.SUBSCRIPTION, slot_id=slot.id, customer_id=customer_id,
            service_date=service_date, meal_window=slot.meal_window, quantity=1, items=[],
            delivery_address=address or {}, status=TaskStatus.PENDING,
        ).on_conflict_do_nothing(
            index_elements=[DeliveryTask.slot_id],
            index_where=text("slot_id IS NOT NULL AND status <> 'CANCELLED'"),
        ).returning(DeliveryTask.id))
        created += res.scalar_one_or_none() is not None

    line_rows = (await db.execute(
        select(OneTimeOrderLine, OneTimeOrder)
        .join(OneTimeOrder, OneTimeOrder.id == OneTimeOrderLine.order_id)
        .where(OneTimeOrderLine.service_date == service_date, OneTimeOrder.status == OneTimeOrderStatus.CONFIRMED)
    )).all()
    for line, order in line_rows:
        res = await db.execute(insert(DeliveryTask).values(
            id=uuid.uuid4(), task_type=TaskType.ONE_TIME, order_line_id=line.id, customer_id=order.customer_id,
            service_date=service_date, meal_window=line.meal_window, quantity=line.quantity,
            items=[line.description] if line.description else [], delivery_address=order.delivery_address or {},
            status=TaskStatus.PENDING,
        ).on_conflict_do_nothing(
            index_elements=[DeliveryTask.order_line_id],
            index_where=text("order_line_id IS NOT NULL AND status <> 'CANCELLED'"),
        ).returning(DeliveryTask.id))
        created += res.scalar_one_or_none() is not None
    return created


async def _active_driver(db: AsyncSession, driver_id: uuid.UUID) -> User:
    driver = await db.get(User, driver_id)
    if driver is None or driver.role != UserRole.DRIVER or not driver.is_active:
        raise NotFound("Driver not found or inactive")
    return driver


async def _open_assignment(db: AsyncSession, task_id: uuid.UUID) -> Optional[DriverAssignment]:
    return (await db.execute(
        select(DriverAssignment).where(
            DriverAssignment.task_id == task_id,
            DriverAssignment.status.in_([AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED]),
        ).with_for_update()
    )).scalars().first()


def _release(task: DeliveryTask) -> None:
    task.assigned_driver_id = None
    task.trip_id = None
    task.stop_sequence = None


async def assign(db: AsyncSession, *, task_id: uuid.UUID, driver_id: uuid.UUID, actor_id: uuid.UUID,
                 now: datetime) -> DriverAssignment:
    """Offers one task to one driver. The driver must accept within the configured timeout (5 minutes)."""
    task = await lock(db, DeliveryTask, task_id, "Task")
    driver = await _active_driver(db, driver_id)
    if task.status not in (TaskStatus.PENDING, TaskStatus.REASSIGNMENT_NEEDED):
        raise Conflict(f"Task is {task.status.value}; only unassigned tasks can be assigned")
    _, settings = await get_settings(db, task.service_date)
    move_task(db, task, TaskStatus.ASSIGNED, actor_id, data={"driver_id": str(driver.id)})
    task.assigned_driver_id = driver.id
    offer = DriverAssignment(task_id=task.id, driver_id=driver.id, status=AssignmentStatus.OFFERED, offered_at=now,
                             expires_at=now + timedelta(minutes=settings.operations.assignment_timeout_minutes),
                             assigned_by_id=actor_id)
    db.add(offer)
    await db.flush()
    return offer


async def _expire(db: AsyncSession, task: DeliveryTask, offer: DriverAssignment, now: datetime) -> None:
    offer.status = AssignmentStatus.EXPIRED
    offer.responded_at = now
    move_task(db, task, TaskStatus.REASSIGNMENT_NEEDED, None, note="Driver did not respond in time")
    _release(task)
    alert(db, "ASSIGNMENT_EXPIRED", "A driver did not respond to a delivery task in time; reassign it.", task.id)


async def accept(db: AsyncSession, *, task_id: uuid.UUID, driver_id: uuid.UUID, now: datetime) -> DeliveryTask:
    task = await lock(db, DeliveryTask, task_id, "Task")
    offer = await _open_assignment(db, task.id)
    if offer is None or offer.driver_id != driver_id:
        raise NotFound("Task not found")
    if offer.status == AssignmentStatus.ACCEPTED:
        return task  # repeated tap
    _, settings = await get_settings(db, task.service_date)
    if assignment_expired(offer.offered_at, now, settings.operations.assignment_timeout_minutes):
        await _expire(db, task, offer, now)
        await db.flush()
        raise Conflict("This assignment has expired and returned to the admin for reassignment")
    offer.status = AssignmentStatus.ACCEPTED
    offer.responded_at = now
    move_task(db, task, TaskStatus.ACCEPTED, driver_id)
    return task


async def decline(db: AsyncSession, *, task_id: uuid.UUID, driver_id: uuid.UUID, reason: str,
                  now: datetime) -> DeliveryTask:
    reason = require_reason(reason, "Declining a task")
    task = await lock(db, DeliveryTask, task_id, "Task")
    offer = await _open_assignment(db, task.id)
    if offer is None or offer.driver_id != driver_id or offer.status != AssignmentStatus.OFFERED:
        raise NotFound("Task not found")
    offer.status = AssignmentStatus.DECLINED
    offer.responded_at = now
    offer.decline_reason = reason
    move_task(db, task, TaskStatus.REASSIGNMENT_NEEDED, driver_id, note=reason)
    _release(task)
    alert(db, "ASSIGNMENT_DECLINED", f"A driver declined a delivery task: {reason}", task.id)
    return task


async def expire_overdue_assignments(db: AsyncSession, now: datetime) -> int:
    """Scheduled job: offers past their deadline go back to the admin. The task itself is kept."""
    offers = (await db.execute(
        select(DriverAssignment).where(DriverAssignment.status == AssignmentStatus.OFFERED,
                                       DriverAssignment.expires_at <= now)
        .with_for_update(skip_locked=True)
    )).scalars().all()
    for offer in offers:
        task = await lock(db, DeliveryTask, offer.task_id, "Task")
        await _expire(db, task, offer, now)
    return len(offers)


async def unassign(db: AsyncSession, *, task_id: uuid.UUID, reason: str, actor_id: uuid.UUID,
                   now: datetime) -> DeliveryTask:
    """Admin pulls back an offered or accepted task before delivery."""
    reason = require_reason(reason, "Taking a task back")
    task = await lock(db, DeliveryTask, task_id, "Task")
    offer = await _open_assignment(db, task.id)
    if offer is None or task.status not in (TaskStatus.ASSIGNED, TaskStatus.ACCEPTED):
        raise Conflict(f"Task is {task.status.value}; it cannot be taken back")
    offer.status = AssignmentStatus.REVOKED
    offer.responded_at = now
    move_task(db, task, TaskStatus.REASSIGNMENT_NEEDED, actor_id, note=reason)
    _release(task)
    audit(db, actor_id, "task.unassigned", "delivery_task", task.id, reason)
    return task


async def set_stop_sequence(db: AsyncSession, *, driver_id: uuid.UUID, service_date: date,
                            meal_window: MealWindow, task_ids: List[uuid.UUID], actor_id: uuid.UUID) -> DeliveryTrip:
    """Admin defines the stop order of a driver's trip for one meal window."""
    await _active_driver(db, driver_id)
    if len(set(task_ids)) != len(task_ids) or not task_ids:
        raise ValidationFailed("Provide each task once, in stop order")
    trip = (await db.execute(
        select(DeliveryTrip).where(DeliveryTrip.driver_id == driver_id, DeliveryTrip.service_date == service_date,
                                   DeliveryTrip.meal_window == meal_window).with_for_update()
    )).scalars().first()
    if trip is None:
        trip = DeliveryTrip(driver_id=driver_id, service_date=service_date, meal_window=meal_window,
                            status=TripStatus.PLANNED)
        db.add(trip)
        await db.flush()
    elif trip.status != TripStatus.PLANNED:
        raise Conflict("The stop order cannot change after the trip has started")

    tasks = (await db.execute(
        select(DeliveryTask).where(DeliveryTask.id.in_(task_ids)).with_for_update()
    )).scalars().all()
    by_id = {t.id: t for t in tasks}
    for tid in task_ids:
        t = by_id.get(tid)
        if (t is None or t.assigned_driver_id != driver_id or t.service_date != service_date
                or t.meal_window != meal_window or t.status in TERMINAL):
            raise ValidationFailed("Every stop must be an open task assigned to this driver for this trip")

    # Tasks dropped from the list leave the trip
    for t in (await db.execute(select(DeliveryTask).where(DeliveryTask.trip_id == trip.id))).scalars().all():
        if t.id not in by_id:
            t.trip_id = None
            t.stop_sequence = None
    for position, tid in enumerate(task_ids, start=1):
        by_id[tid].trip_id = trip.id
        by_id[tid].stop_sequence = position
    audit(db, actor_id, "trip.stop_sequence_set", "delivery_trip", trip.id,
          data={"task_ids": [str(t) for t in task_ids]})
    return trip
