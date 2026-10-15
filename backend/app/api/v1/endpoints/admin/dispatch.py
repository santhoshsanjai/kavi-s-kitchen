"""Daily dispatch: generate tasks, assign drivers, set stop order, review trips and distances."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import row
from app.api.v1.endpoints.admin._common import Admin, actor, optional_uuid
from app.core.database import get_db
from app.core.time import business_today, utcnow
from app.domain.meal_windows import MEAL_WINDOW_ORDER, MealWindow
from app.domain.task_states import TaskStatus
from app.models.customer import Customer
from app.models.delivery import AssignmentStatus, DeliveryTask, DeliveryTrip, DriverAssignment, RouteLeg
from app.models.user import User
from app.services import task_service, trip_service

router = APIRouter()


class AssignIn(BaseModel):
    driver_id: str


class ReasonIn(BaseModel):
    reason: Optional[str] = None


class SequenceIn(BaseModel):
    driver_id: str
    service_date: date
    meal_window: MealWindow
    task_ids: List[str]


class ManualDistanceIn(BaseModel):
    stop_legs_km: List[Decimal]
    return_leg_km: Decimal = Field(ge=0)
    reason: Optional[str] = None


async def _names(db: AsyncSession, model, ids, attr):
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {r.id: getattr(r, attr) for r in (await db.execute(select(model).where(model.id.in_(ids)))).scalars().all()}


async def _tasks_out(db: AsyncSession, tasks: List[DeliveryTask]) -> List[dict]:
    customers = await _names(db, Customer, [t.customer_id for t in tasks], "name")
    drivers = await _names(db, User, [t.assigned_driver_id for t in tasks], "full_name")
    offers = {}
    ids = [t.id for t in tasks]
    if ids:
        for o in (await db.execute(select(DriverAssignment).where(
                DriverAssignment.task_id.in_(ids),
                DriverAssignment.status.in_([AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED])))).scalars().all():
            offers[o.task_id] = o
    return [row(t, customer_name=customers.get(t.customer_id), driver_name=drivers.get(t.assigned_driver_id),
                offer_expires_at=offers[t.id].expires_at if t.id in offers and offers[t.id].status == AssignmentStatus.OFFERED else None)
            for t in tasks]


@router.post("/dispatch/generate")
async def generate(service_date: Optional[date] = None, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    service_date = service_date or business_today()
    created = await task_service.generate_tasks(db, service_date)
    await db.commit()
    return {"service_date": service_date.isoformat(), "created": created}


@router.get("/dispatch/tasks")
async def list_tasks(service_date: Optional[date] = None, meal_window: Optional[MealWindow] = None,
                     status: Optional[TaskStatus] = None, driver_id: Optional[str] = None,
                     _: dict = Admin, db: AsyncSession = Depends(get_db)):
    q = select(DeliveryTask).where(DeliveryTask.service_date == (service_date or business_today()))
    if meal_window:
        q = q.where(DeliveryTask.meal_window == meal_window)
    if status:
        q = q.where(DeliveryTask.status == status)
    if driver_id:
        q = q.where(DeliveryTask.assigned_driver_id == optional_uuid(driver_id))
    tasks = (await db.execute(q)).scalars().all()
    tasks = sorted(tasks, key=lambda t: (MEAL_WINDOW_ORDER.index(t.meal_window), t.stop_sequence or 9999,
                                         str(t.customer_id)))
    return await _tasks_out(db, tasks)


@router.post("/dispatch/tasks/{task_id}/assign")
async def assign(task_id: str, body: AssignIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    tid = parse_uuid(task_id, "Task not found")
    await task_service.assign(db, task_id=tid, driver_id=parse_uuid(body.driver_id, "Driver not found"),
                              actor_id=actor(user), now=utcnow())
    await db.commit()
    return (await _tasks_out(db, [await db.get(DeliveryTask, tid)]))[0]


@router.post("/dispatch/tasks/{task_id}/unassign")
async def unassign(task_id: str, body: ReasonIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    task = await task_service.unassign(db, task_id=parse_uuid(task_id, "Task not found"), reason=body.reason,
                                       actor_id=actor(user), now=utcnow())
    await db.commit()
    return (await _tasks_out(db, [task]))[0]


@router.put("/dispatch/trips/sequence")
async def set_sequence(body: SequenceIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    trip = await task_service.set_stop_sequence(
        db, driver_id=parse_uuid(body.driver_id, "Driver not found"), service_date=body.service_date,
        meal_window=body.meal_window, task_ids=[parse_uuid(t, "Task not found") for t in body.task_ids],
        actor_id=actor(user))
    await db.commit()
    return await _trip_out(db, trip)


async def _trip_out(db: AsyncSession, trip: DeliveryTrip) -> dict:
    driver = await db.get(User, trip.driver_id)
    legs = (await db.execute(select(RouteLeg).where(RouteLeg.trip_id == trip.id).order_by(RouteLeg.sequence))).scalars().all()
    tasks = (await db.execute(select(DeliveryTask).where(DeliveryTask.trip_id == trip.id)
                              .order_by(DeliveryTask.stop_sequence))).scalars().all()
    return row(trip, driver_name=driver.full_name if driver else None,
               legs=[row(l, exclude=["provider_data"]) for l in legs], tasks=await _tasks_out(db, list(tasks)),
               visited_stops=len(trip_service._stops(list(tasks))))


@router.get("/trips")
async def list_trips(service_date: Optional[date] = None, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    trips = (await db.execute(select(DeliveryTrip).where(
        DeliveryTrip.service_date == (service_date or business_today())))).scalars().all()
    trips = sorted(trips, key=lambda t: (MEAL_WINDOW_ORDER.index(t.meal_window), str(t.driver_id)))
    return [await _trip_out(db, t) for t in trips]


@router.post("/trips/{trip_id}/manual-distance")
async def manual_distance(trip_id: str, body: ManualDistanceIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    trip = await trip_service.enter_manual_distances(
        db, trip_id=parse_uuid(trip_id, "Trip not found"), stop_legs_km=body.stop_legs_km,
        return_leg_km=body.return_leg_km, reason=body.reason, actor_id=actor(user))
    await db.commit()
    return await _trip_out(db, trip)
