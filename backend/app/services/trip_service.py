import uuid
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.delivery_fees import RouteStop, customer_delivery_charges
from app.domain.payouts import trip_kilometres
from app.domain.task_states import TaskStatus, TripEndBlocked, check_trip_can_end
from app.models.delivery import (
    DeliveryTask, DeliveryTrip, DistanceSource, DistanceStatus, RouteLeg, TripStatus,
)
from app.models.ledger import CustomerLedgerEntry, LedgerEntryType
from app.models.payout import DaySummaryStatus, DriverDaySummary
from app.services.common import alert, audit, lock, move_task, post_ledger, require_reason
from app.services.errors import Conflict, NotFound, ValidationFailed
from app.services.route_distance import RouteDistanceProvider, RouteUnavailable
from app.services.settings_service import get_settings

VISITED = (TaskStatus.DELIVERED, TaskStatus.FAILED, TaskStatus.PARTIAL)


async def _own_trip(db: AsyncSession, trip_id: uuid.UUID, driver_id: uuid.UUID) -> DeliveryTrip:
    trip = await lock(db, DeliveryTrip, trip_id, "Trip")
    if trip.driver_id != driver_id:
        raise NotFound("Trip not found")
    return trip


async def _trip_tasks(db: AsyncSession, trip_id: uuid.UUID) -> List[DeliveryTask]:
    return list((await db.execute(
        select(DeliveryTask).where(DeliveryTask.trip_id == trip_id).order_by(DeliveryTask.stop_sequence).with_for_update()
    )).scalars().all())


async def start_trip(db: AsyncSession, *, trip_id: uuid.UUID, driver_id: uuid.UUID, now: datetime) -> DeliveryTrip:
    trip = await _own_trip(db, trip_id, driver_id)
    if trip.status == TripStatus.STARTED:
        return trip
    if trip.status != TripStatus.PLANNED:
        raise Conflict("This trip has already ended")
    tasks = await _trip_tasks(db, trip.id)
    if not any(t.status == TaskStatus.ACCEPTED for t in tasks):
        raise Conflict("Accept at least one task on this trip before starting it")
    trip.status = TripStatus.STARTED
    trip.started_at = now
    return trip


async def record_outcome(db: AsyncSession, *, task_id: uuid.UUID, driver_id: uuid.UUID, outcome: TaskStatus,
                         now: datetime, note: Optional[str] = None, reason: Optional[str] = None,
                         delivered_items: Optional[list] = None, missing_items: Optional[list] = None) -> DeliveryTask:
    """
    Driver records Delivered (optional note), Failed (reason required) or Partial (delivered and missing
    items required). Repeating the same outcome changes nothing, so a drop is never completed twice.
    """
    if outcome not in VISITED:
        raise ValidationFailed("Outcome must be DELIVERED, FAILED or PARTIAL")
    task = await lock(db, DeliveryTask, task_id, "Task")
    if task.assigned_driver_id != driver_id:
        raise NotFound("Task not found")
    if task.status == outcome:
        return task
    trip = await db.get(DeliveryTrip, task.trip_id) if task.trip_id else None
    if trip is None or trip.status != TripStatus.STARTED:
        raise Conflict("Start the trip before recording deliveries")

    if outcome == TaskStatus.FAILED:
        task.failure_reason = require_reason(reason, "A failed delivery")
    if outcome == TaskStatus.PARTIAL:
        if not delivered_items or not missing_items:
            raise ValidationFailed("A partial delivery must list delivered and missing items")
        task.delivered_items = delivered_items
        task.missing_items = missing_items
        task.failure_reason = reason
    move_task(db, task, outcome, driver_id, note=note or reason)
    task.delivery_note = note
    task.completed_at = now
    task.completed_by_id = driver_id
    if outcome == TaskStatus.FAILED:
        alert(db, "DELIVERY_FAILED", f"Delivery failed: {task.failure_reason}", task.id)
    elif outcome == TaskStatus.PARTIAL:
        alert(db, "DELIVERY_PARTIAL", f"Partial delivery; missing: {', '.join(map(str, missing_items))}", task.id)
    return task


def _stops(tasks: List[DeliveryTask]) -> "OrderedDict[uuid.UUID, List[DeliveryTask]]":
    """Visited tasks grouped into stops by customer, in admin-defined order."""
    stops: "OrderedDict[uuid.UUID, List[DeliveryTask]]" = OrderedDict()
    for t in tasks:
        if t.status in VISITED:
            stops.setdefault(t.customer_id, []).append(t)
    return stops


async def end_trip(db: AsyncSession, *, trip_id: uuid.UUID, driver_id: uuid.UUID, now: datetime,
                   provider: Optional[RouteDistanceProvider], reason: Optional[str] = None) -> DeliveryTrip:
    trip = await _own_trip(db, trip_id, driver_id)
    if trip.status == TripStatus.ENDED:
        return trip
    if trip.status != TripStatus.STARTED:
        raise Conflict("Start the trip before ending it")
    _, settings = await get_settings(db, trip.service_date)
    tasks = await _trip_tasks(db, trip.id)
    try:
        check_trip_can_end([t.status for t in tasks], settings.operations.allow_end_trip_with_unattempted, reason)
    except TripEndBlocked as exc:
        raise Conflict(str(exc)) from exc

    trip.status = TripStatus.ENDED
    trip.ended_at = now
    trip.end_reason = reason
    trip.include_return_leg = settings.payout.include_return_leg
    unattempted = [t for t in tasks if t.status not in VISITED and t.status != TaskStatus.CANCELLED]
    if unattempted:
        alert(db, "TRIP_ENDED_WITH_OPEN_TASKS", f"{len(unattempted)} task(s) were not attempted: {reason}")

    stops = _stops(tasks)
    kitchen = settings.kitchen
    coords = []
    for group in stops.values():
        addr = group[0].delivery_address or {}
        coords.append((addr.get("latitude"), addr.get("longitude")))
    try:
        if provider is None or kitchen.latitude is None or kitchen.longitude is None:
            raise RouteUnavailable("Google Maps or the kitchen location is not configured")
        if not stops:
            raise RouteUnavailable("No stops were visited")
        if any(lat is None or lng is None for lat, lng in coords):
            raise RouteUnavailable("A stop has no map location")
        result = await provider.route((kitchen.latitude, kitchen.longitude), coords)
    except RouteUnavailable as exc:
        trip.distance_status = DistanceStatus.NEEDS_MANUAL_ENTRY
        alert(db, "TRIP_DISTANCE_NEEDED", f"Route distance could not be calculated ({exc}); enter it manually.")
        return trip

    stop_keys = list(stops.keys())
    for seq, km in enumerate(result.stop_legs_km, start=1):
        db.add(RouteLeg(trip_id=trip.id, sequence=seq, to_task_id=stops[stop_keys[seq - 1]][0].id,
                        distance_km=km, source=DistanceSource.GOOGLE_MAPS, provider_data=result.provider_data))
    db.add(RouteLeg(trip_id=trip.id, sequence=len(stop_keys) + 1, is_return=True, distance_km=result.return_leg_km,
                    source=DistanceSource.GOOGLE_MAPS, provider_data=result.provider_data))
    await db.flush()
    await _apply_distances(db, trip, settings, None)
    return trip


async def enter_manual_distances(db: AsyncSession, *, trip_id: uuid.UUID, stop_legs_km: List[Decimal],
                                 return_leg_km: Decimal, reason: str, actor_id: uuid.UUID) -> DeliveryTrip:
    """Admin enters or corrects a trip's leg distances. Audited; blocked once the day is finalized."""
    reason = require_reason(reason, "Entering a manual distance")
    trip = await lock(db, DeliveryTrip, trip_id, "Trip")
    if trip.status != TripStatus.ENDED:
        raise Conflict("Distances can only be entered after the trip ends")
    finalized = await db.scalar(select(func.count()).select_from(DriverDaySummary).where(
        DriverDaySummary.driver_id == trip.driver_id, DriverDaySummary.service_date == trip.service_date,
        DriverDaySummary.status == DaySummaryStatus.FINALIZED))
    if finalized:
        raise Conflict("Earnings for this day are finalized; use an itemized adjustment instead")
    stops = _stops(await _trip_tasks(db, trip.id))
    if len(stop_legs_km) != len(stops):
        raise ValidationFailed(f"Expected {len(stops)} leg distance(s), one per visited stop")
    if any(Decimal(str(km)) < 0 for km in [*stop_legs_km, return_leg_km]):
        raise ValidationFailed("Distances cannot be negative")

    old = [(leg.sequence, str(leg.distance_km), leg.source.value) for leg in (await db.execute(
        select(RouteLeg).where(RouteLeg.trip_id == trip.id).order_by(RouteLeg.sequence))).scalars().all()]
    await db.execute(delete(RouteLeg).where(RouteLeg.trip_id == trip.id))
    keys = list(stops.keys())
    for seq, km in enumerate(stop_legs_km, start=1):
        db.add(RouteLeg(trip_id=trip.id, sequence=seq, to_task_id=stops[keys[seq - 1]][0].id,
                        distance_km=Decimal(str(km)), source=DistanceSource.MANUAL, entered_by_id=actor_id,
                        manual_reason=reason))
    db.add(RouteLeg(trip_id=trip.id, sequence=len(keys) + 1, is_return=True, distance_km=Decimal(str(return_leg_km)),
                    source=DistanceSource.MANUAL, entered_by_id=actor_id, manual_reason=reason))
    await db.flush()
    _, settings = await get_settings(db, trip.service_date)
    await _apply_distances(db, trip, settings, actor_id)
    audit(db, actor_id, "trip.manual_distance", "delivery_trip", trip.id, reason,
          {"previous_legs": old, "stop_legs_km": [str(k) for k in stop_legs_km], "return_leg_km": str(return_leg_km)})
    return trip


async def _apply_distances(db: AsyncSession, trip: DeliveryTrip, settings, actor_id: Optional[uuid.UUID]) -> None:
    """Sets payable km and posts customer delivery fees (as differences, so corrections are itemized)."""
    legs = (await db.execute(select(RouteLeg).where(RouteLeg.trip_id == trip.id).order_by(RouteLeg.sequence))).scalars().all()
    stop_legs = [leg for leg in legs if not leg.is_return]
    return_leg = next((leg.distance_km for leg in legs if leg.is_return), None)
    trip.payable_km = trip_kilometres([leg.distance_km for leg in stop_legs], return_leg, bool(trip.include_return_leg))
    trip.distance_status = DistanceStatus.CALCULATED

    stops = _stops(await _trip_tasks(db, trip.id))
    route_stops = []
    for leg in stop_legs:
        task = next(t for group in stops.values() for t in group if t.id == leg.to_task_id)
        group = stops[task.customer_id]
        route_stops.append(RouteStop(task.customer_id, leg.distance_km,
                                     any(t.status == TaskStatus.DELIVERED for t in group)))
    fees: Dict[uuid.UUID, Decimal] = customer_delivery_charges(
        route_stops, settings.delivery_fees.customer_rate_per_km, settings.delivery_fees.minimum_fee)

    for customer_id, fee in fees.items():
        group = stops[customer_id]
        charged_task = next((t for t in group if t.status == TaskStatus.DELIVERED), group[0])
        for t in group:
            t.customer_delivery_charge = fee if t.id == charged_task.id else Decimal("0.00")
        task_ids = [t.id for t in group]
        posted = await db.scalar(select(func.coalesce(func.sum(CustomerLedgerEntry.amount), 0)).where(
            CustomerLedgerEntry.entry_type == LedgerEntryType.DELIVERY_FEE,
            CustomerLedgerEntry.task_id.in_(task_ids)))
        delta = fee - Decimal(posted)
        if delta != 0:
            await post_ledger(db, customer_id=customer_id, entry_type=LedgerEntryType.DELIVERY_FEE, amount=delta,
                              task_id=charged_task.id, created_by_id=actor_id,
                              description=f"Delivery fee {trip.service_date.isoformat()} {trip.meal_window.value.lower()}"
                                          + (" (correction)" if posted else ""),
                              idempotency_key=f"trip:{trip.id}:fee:{customer_id}:{uuid.uuid4()}")
