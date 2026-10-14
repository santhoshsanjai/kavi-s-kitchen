import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.money import round_money
from app.domain.payouts import EarningCode, count_drops, day_fixed_allowance, trip_earning_lines
from app.domain.task_states import TaskStatus
from app.models.delivery import DeliveryTask, DeliveryTrip, DistanceStatus, TripStatus
from app.models.payout import DaySummaryStatus, DriverDaySummary, DriverEarningLine
from app.services.common import audit, require_reason
from app.services.errors import Conflict, NotFound, ValidationFailed
from app.services.settings_service import get_settings


async def _summary(db: AsyncSession, driver_id: uuid.UUID, service_date: date) -> DriverDaySummary | None:
    return (await db.execute(
        select(DriverDaySummary).where(DriverDaySummary.driver_id == driver_id,
                                       DriverDaySummary.service_date == service_date).with_for_update()
    )).scalars().first()


async def _recalculate_total(db: AsyncSession, summary: DriverDaySummary) -> None:
    lines = (await db.execute(select(DriverEarningLine).where(DriverEarningLine.summary_id == summary.id))).scalars().all()
    summary.total_amount = round_money(sum((l.amount for l in lines), Decimal("0")))


async def calculate_day(db: AsyncSession, *, driver_id: uuid.UUID, service_date: date) -> DriverDaySummary:
    """
    Proposed daily earnings: per-km (Maps route estimate or audited manual distance) + per successful
    drop + fixed allowance, plus approved adjustments. A finalized day is returned unchanged.
    """
    version, settings = await get_settings(db, service_date)
    policy = settings.payout.policy()
    summary = await _summary(db, driver_id, service_date)
    if summary is not None and summary.status == DaySummaryStatus.FINALIZED:
        return summary
    if summary is None:
        summary = DriverDaySummary(driver_id=driver_id, service_date=service_date, status=DaySummaryStatus.PROPOSED,
                                   policy_snapshot={}, total_amount=Decimal("0"))
        db.add(summary)
        await db.flush()
    else:
        # Recompute system lines; keep approved adjustments
        await db.execute(delete(DriverEarningLine).where(DriverEarningLine.summary_id == summary.id,
                                                         DriverEarningLine.code != EarningCode.ADJUSTMENT))

    summary.settings_version_id = version.id if version else None
    summary.policy_snapshot = settings.payout.model_dump(mode="json")
    trips = (await db.execute(select(DeliveryTrip).where(
        DeliveryTrip.driver_id == driver_id, DeliveryTrip.service_date == service_date,
        DeliveryTrip.status == TripStatus.ENDED, DeliveryTrip.distance_status == DistanceStatus.CALCULATED)
    )).scalars().all()

    for trip in trips:
        delivered = (await db.execute(select(DeliveryTask.id, DeliveryTask.customer_id).where(
            DeliveryTask.trip_id == trip.id, DeliveryTask.status == TaskStatus.DELIVERED))).all()
        drops = count_drops([(tid, cid) for tid, cid in delivered], policy.drop_unit)
        for line in trip_earning_lines(policy, trip.payable_km or Decimal("0"), drops):
            db.add(DriverEarningLine(summary_id=summary.id, trip_id=trip.id, code=line.code, quantity=line.quantity,
                                     rate=line.rate, amount=line.amount,
                                     description=f"{trip.meal_window.value.title()} trip: {line.description}"))
    for line in day_fixed_allowance(policy, len(trips)):
        db.add(DriverEarningLine(summary_id=summary.id, code=line.code, quantity=line.quantity, rate=line.rate,
                                 amount=line.amount, description=line.description))
    await db.flush()
    await _recalculate_total(db, summary)
    return summary


async def finalize_day(db: AsyncSession, *, driver_id: uuid.UUID, service_date: date, actor_id: uuid.UUID,
                       now: datetime) -> DriverDaySummary:
    summary = await calculate_day(db, driver_id=driver_id, service_date=service_date)
    if summary.status == DaySummaryStatus.FINALIZED:
        return summary
    open_trips = (await db.execute(select(DeliveryTrip).where(
        DeliveryTrip.driver_id == driver_id, DeliveryTrip.service_date == service_date,
        (DeliveryTrip.status != TripStatus.ENDED) | (DeliveryTrip.distance_status != DistanceStatus.CALCULATED))
    )).scalars().all()
    if open_trips:
        raise Conflict("All trips must be ended and have distances before the day can be finalized")
    summary.status = DaySummaryStatus.FINALIZED
    summary.finalized_at = now
    summary.finalized_by_id = actor_id
    audit(db, actor_id, "earnings.day_finalized", "driver_day_summary", summary.id,
          data={"total": str(summary.total_amount), "policy": summary.policy_snapshot})
    return summary


async def add_adjustment(db: AsyncSession, *, driver_id: uuid.UUID, service_date: date, amount: Decimal,
                         reason: str, actor_id: uuid.UUID) -> DriverEarningLine:
    """Itemized, reasoned adjustment. The only way to change a finalized day; other lines are never edited."""
    reason = require_reason(reason, "An earnings adjustment")
    amount = round_money(amount)
    if amount == 0:
        raise ValidationFailed("Adjustment amount cannot be zero")
    summary = await _summary(db, driver_id, service_date)
    if summary is None:
        raise NotFound("Calculate the day's earnings before adjusting them")
    line = DriverEarningLine(summary_id=summary.id, code=EarningCode.ADJUSTMENT, quantity=Decimal(1), rate=amount,
                             amount=amount, description="Adjustment", reason=reason, created_by_id=actor_id)
    db.add(line)
    await db.flush()
    await _recalculate_total(db, summary)
    audit(db, actor_id, "earnings.adjustment", "driver_day_summary", summary.id, reason,
          {"amount": str(amount), "after_finalization": summary.status == DaySummaryStatus.FINALIZED})
    return line


async def lines_for_day(db: AsyncSession, summary_id: uuid.UUID) -> List[DriverEarningLine]:
    return list((await db.execute(select(DriverEarningLine).where(DriverEarningLine.summary_id == summary_id)
                                  .order_by(DriverEarningLine.created_at))).scalars().all())
