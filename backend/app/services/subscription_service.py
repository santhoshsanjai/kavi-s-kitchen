import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import BUSINESS_TZ
from app.domain.meal_windows import MEAL_WINDOW_ORDER, MealWindow, is_skip_on_time
from app.domain.money import round_money, to_decimal
from app.domain.proration import cumulative_skip_credit, per_meal_value
from app.domain.service_calendar import month_start
from app.domain.task_states import UNSTARTED, TaskStatus
from app.models.customer import Customer
from app.models.delivery import DeliveryTask
from app.models.ledger import LedgerEntryType
from app.models.meal_plan import MealPlan
from app.models.subscription import (
    PlanRateVersion, SlotStatus, Subscription, SubscriptionMealSlot, SubscriptionStatus,
)
from app.services.common import audit, lock, move_task, post_ledger, require_reason
from app.services.errors import Conflict, NotFound, ValidationFailed
from app.services.settings_service import get_settings, service_dates_for_month


@dataclass
class SubscriptionPreview:
    service_month: date
    service_dates: List[date]
    included_meals: List[MealWindow]
    total_slots: int
    plan_amount: Decimal
    per_meal_value: Decimal          # unrounded
    per_meal_value_display: Decimal  # rounded for display only


async def current_rate(db: AsyncSession, plan: MealPlan, on_date: date) -> PlanRateVersion:
    """Rate in force on a date. Plans without a version yet get one snapshotted from their current price."""
    rate = (await db.execute(
        select(PlanRateVersion).where(PlanRateVersion.plan_id == plan.id, PlanRateVersion.effective_from <= on_date)
        .order_by(PlanRateVersion.effective_from.desc()).limit(1)
    )).scalars().first()
    if rate is None:
        rate = PlanRateVersion(plan_id=plan.id, effective_from=on_date, monthly_amount=to_decimal(plan.price),
                               included_meals=list(plan.meal_sessions))
        db.add(rate)
        await db.flush()
    return rate


async def preview(db: AsyncSession, *, plan_id: uuid.UUID, service_month: date) -> Tuple[SubscriptionPreview, PlanRateVersion]:
    plan = await db.get(MealPlan, plan_id)
    if plan is None or not plan.is_active:
        raise NotFound("Plan not found or inactive")
    service_month = month_start(service_month)
    rate = await current_rate(db, plan, service_month)
    _, settings = await get_settings(db, service_month)
    dates = await service_dates_for_month(db, service_month, settings)
    meals = [MealWindow(m) for m in MEAL_WINDOW_ORDER if m.value in rate.included_meals]
    total = len(dates) * len(meals)
    if total == 0:
        raise ValidationFailed("This month has no service dates or the plan includes no meals")
    value = per_meal_value(rate.monthly_amount, total)
    return SubscriptionPreview(service_month, dates, meals, total, to_decimal(rate.monthly_amount), value,
                               round_money(value)), rate


async def activate(db: AsyncSession, *, customer_id: uuid.UUID, plan_id: uuid.UUID, service_month: date,
                   actor_id: uuid.UUID, now: datetime) -> Subscription:
    customer = await db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise NotFound("Customer not found or inactive")
    pv, rate = await preview(db, plan_id=plan_id, service_month=service_month)

    exists = await db.scalar(select(func.count()).select_from(Subscription).where(
        Subscription.customer_id == customer_id, Subscription.service_month == pv.service_month,
        Subscription.status != SubscriptionStatus.CANCELLED))
    if exists:
        raise Conflict("Customer already has a subscription for that month")

    settings_version, _ = await get_settings(db, pv.service_month)
    sub = Subscription(
        customer_id=customer_id, plan_id=plan_id, plan_rate_version_id=rate.id,
        settings_version_id=settings_version.id if settings_version else None,
        service_month=pv.service_month, status=SubscriptionStatus.ACTIVE, plan_amount=pv.plan_amount,
        included_meals=[m.value for m in pv.included_meals], service_days=len(pv.service_dates),
        total_slots=pv.total_slots, per_meal_value=pv.per_meal_value, credited_skip_total=Decimal("0"),
        activated_at=now, activated_by_id=actor_id,
    )
    db.add(sub)
    await db.flush()
    db.add_all([
        SubscriptionMealSlot(subscription_id=sub.id, service_date=d, meal_window=m, status=SlotStatus.SCHEDULED)
        for d in pv.service_dates for m in pv.included_meals
    ])
    await post_ledger(db, customer_id=customer_id, entry_type=LedgerEntryType.SUBSCRIPTION_CHARGE,
                      amount=round_money(pv.plan_amount), subscription_id=sub.id, created_by_id=actor_id,
                      description=f"Subscription {pv.service_month:%B %Y}: {pv.total_slots} meals",
                      idempotency_key=f"subscription:{sub.id}:charge")
    audit(db, actor_id, "subscription.activated", "subscription", sub.id,
          data={"service_month": pv.service_month.isoformat(), "total_slots": pv.total_slots,
                "plan_amount": str(pv.plan_amount)})
    return sub


@dataclass
class SkipResult:
    skipped: int
    credit_eligible: int
    late: int
    credit_posted: Decimal  # positive = credit given to the customer in this operation


async def _resolve_slots(db: AsyncSession, sub: Subscription,
                         targets: Iterable[Tuple[date, Optional[MealWindow]]]) -> List[SubscriptionMealSlot]:
    """targets: (date, window) for one meal or (date, None) for the whole day."""
    slots: Dict[Tuple[date, MealWindow], SubscriptionMealSlot] = {
        (s.service_date, s.meal_window): s for s in (await db.execute(
            select(SubscriptionMealSlot).where(SubscriptionMealSlot.subscription_id == sub.id).with_for_update()
        )).scalars().all()
    }
    picked: Dict[uuid.UUID, SubscriptionMealSlot] = {}
    for day, window in targets:
        matches = [s for (d, w), s in slots.items() if d == day and (window is None or w == window)]
        if not matches:
            raise NotFound(f"No included meal on {day.isoformat()}" + (f" for {window.value}" if window else ""))
        for s in matches:
            picked[s.id] = s
    return list(picked.values())


async def _live_task(db: AsyncSession, slot_id: uuid.UUID) -> Optional[DeliveryTask]:
    return (await db.execute(
        select(DeliveryTask).where(DeliveryTask.slot_id == slot_id, DeliveryTask.status != TaskStatus.CANCELLED)
        .with_for_update()
    )).scalars().first()


async def _post_credit_delta(db: AsyncSession, sub: Subscription, actor_id: uuid.UUID, reason: str) -> Decimal:
    """Keeps the posted skip credit equal to the cumulative credit for all eligible skips (no drift)."""
    _, settings = await get_settings(db, sub.service_month)
    eligible = await db.scalar(select(func.count()).select_from(SubscriptionMealSlot).where(
        SubscriptionMealSlot.subscription_id == sub.id, SubscriptionMealSlot.status == SlotStatus.SKIPPED,
        SubscriptionMealSlot.skip_credit_eligible.is_(True)))
    target = cumulative_skip_credit(sub.plan_amount, sub.total_slots, eligible, settings.billing.rounding_policy)
    delta = target - sub.credited_skip_total
    if delta != 0:
        await post_ledger(
            db, customer_id=sub.customer_id, entry_type=LedgerEntryType.SKIP_CREDIT, amount=-delta,
            subscription_id=sub.id, created_by_id=actor_id, reason=reason,
            description=("Skipped meal credit" if delta > 0 else "Skipped meal credit reversed (meal restored)"),
            idempotency_key=f"subscription:{sub.id}:skip-credit:{uuid.uuid4()}",
        )
        sub.credited_skip_total = target
    return delta


async def skip_meals(db: AsyncSession, *, subscription_id: uuid.UUID,
                     targets: Iterable[Tuple[date, Optional[MealWindow]]], reason: str,
                     actor_id: uuid.UUID, now: datetime) -> SkipResult:
    """
    Admin-only skip of single meals or whole days. On-time skips (before each window's cutoff) earn
    automatic credit; late skips earn none. Unstarted tasks are cancelled; tasks a driver already
    accepted, started or completed need the explicit exception path and block the skip.
    """
    reason = require_reason(reason, "Skipping a meal")
    sub = await lock(db, Subscription, subscription_id, "Subscription")
    if sub.status != SubscriptionStatus.ACTIVE:
        raise Conflict("Only active subscriptions can be changed")
    _, settings = await get_settings(db, sub.service_month)

    slots = [s for s in await _resolve_slots(db, sub, targets) if s.status == SlotStatus.SCHEDULED]
    tasks = {s.id: await _live_task(db, s.id) for s in slots}
    blocked = [t for t in tasks.values() if t is not None and t.status not in UNSTARTED]
    if blocked:
        raise Conflict("A driver has already accepted or completed a delivery for one of these meals; "
                       "handle it as a delivery exception instead of a skip")

    eligible = late = 0
    for slot in slots:
        window = settings.meal_windows[slot.meal_window]
        on_time = is_skip_on_time(now, slot.service_date, window.start, window.skip_cutoff_minutes, BUSINESS_TZ)
        slot.status = SlotStatus.SKIPPED
        slot.skip_credit_eligible = on_time
        slot.skip_reason = reason
        slot.skipped_at = now
        slot.skipped_by_id = actor_id
        eligible += on_time
        late += not on_time
        task = tasks[slot.id]
        if task is not None:
            move_task(db, task, TaskStatus.CANCELLED, actor_id, note=f"Meal skipped: {reason}")

    await db.flush()
    delta = await _post_credit_delta(db, sub, actor_id, reason)
    audit(db, actor_id, "subscription.meals_skipped", "subscription", sub.id, reason,
          {"slots": [f"{s.service_date.isoformat()}:{s.meal_window.value}" for s in slots],
           "credit_eligible": eligible, "late": late, "credit_posted": str(delta)})
    return SkipResult(len(slots), eligible, late, delta)


async def restore_meals(db: AsyncSession, *, subscription_id: uuid.UUID,
                        targets: Iterable[Tuple[date, Optional[MealWindow]]], reason: str,
                        actor_id: uuid.UUID) -> SkipResult:
    """Undo skips. Any automatic credit they earned is reversed in the ledger."""
    reason = require_reason(reason, "Restoring a meal")
    sub = await lock(db, Subscription, subscription_id, "Subscription")
    if sub.status != SubscriptionStatus.ACTIVE:
        raise Conflict("Only active subscriptions can be changed")
    slots = [s for s in await _resolve_slots(db, sub, targets) if s.status == SlotStatus.SKIPPED]
    for slot in slots:
        slot.status = SlotStatus.SCHEDULED
        slot.skip_credit_eligible = None
        slot.skip_reason = None
        slot.skipped_at = None
        slot.skipped_by_id = None
    await db.flush()
    delta = await _post_credit_delta(db, sub, actor_id, reason)
    audit(db, actor_id, "subscription.meals_restored", "subscription", sub.id, reason,
          {"slots": [f"{s.service_date.isoformat()}:{s.meal_window.value}" for s in slots],
           "credit_posted": str(delta)})
    return SkipResult(len(slots), 0, 0, delta)
