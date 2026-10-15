"""Phase 1 services against PostgreSQL: subscriptions, skips/credits, one-time orders, tasks, trips, payouts, payments."""
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.core.time import BUSINESS_TZ
from app.domain.meal_windows import MealWindow
from app.domain.payouts import EarningCode
from app.domain.task_states import TaskStatus
from app.models.audit import AdminAlert, AuditLog
from app.models.customer import Customer
from app.models.delivery import DeliveryTask, DeliveryTrip, DistanceStatus, RouteLeg, TripStatus
from app.models.ledger import CustomerLedgerEntry, LedgerEntryType, PaymentMethod
from app.models.meal_plan import MealPlan
from app.models.one_time_order import OneTimeOrderLine, OneTimeOrderStatus, OrderSource
from app.models.payout import DaySummaryStatus
from app.models.subscription import SlotStatus, SubscriptionMealSlot
from app.models.user import User
from app.schemas.settings import BusinessSettings
from app.schemas.user import UserRole
from app.services import (
    earnings_service, one_time_order_service, payment_service, settings_service,
    subscription_service, task_service, trip_service,
)
from app.services.errors import Conflict, NotFound, ValidationFailed
from app.services.route_distance import RouteResult, RouteUnavailable

MONTH = date(2030, 1, 1)          # far future so settings and cutoffs are deterministic
SERVICE_DAY = date(2030, 1, 15)   # a Tuesday


def ist(day: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(day, time(hh, mm), tzinfo=BUSINESS_TZ)


class FakeMaps:
    def __init__(self, legs, return_leg):
        self.legs, self.return_leg, self.calls = legs, return_leg, []

    async def route(self, origin, stops):
        self.calls.append((origin, stops))
        return RouteResult([Decimal(str(x)) for x in self.legs], Decimal(str(self.return_leg)), {"fake": True})


class BrokenMaps:
    async def route(self, origin, stops):
        raise RouteUnavailable("ZERO_RESULTS")


@pytest_asyncio.fixture
async def world():
    """Admin, two drivers, two customers with map locations, a Veg Full Day plan at ₹5,500 and test rates."""
    async with SessionLocal() as db:
        admin = (await db.execute(select(User).where(User.username == "kitchenadmin"))).scalars().one()
        d1 = User(username="d001", full_name="Driver One", driver_code="D001", role=UserRole.DRIVER,
                  hashed_password=get_password_hash("x"))
        d2 = User(username="d002", full_name="Driver Two", driver_code="D002", role=UserRole.DRIVER,
                  hashed_password=get_password_hash("x"))
        c1 = Customer(name="Asha", phone="9000000101", address={"area": "Adyar", "latitude": 13.0, "longitude": 80.25},
                      meal_preference={})
        c2 = Customer(name="Bala", phone="9000000102", address={"area": "Besant Nagar", "latitude": 13.01, "longitude": 80.27},
                      meal_preference={})
        plan = MealPlan(name="Spec Veg Full Day", diet_type="VEG", meal_sessions=["BREAKFAST", "LUNCH", "DINNER"],
                        price=Decimal("5500"))
        db.add_all([d1, d2, c1, c2, plan])
        await db.flush()
        settings = BusinessSettings()
        settings.delivery_fees.customer_rate_per_km = Decimal("10")
        settings.payout.per_km_rate = Decimal("4")
        settings.payout.per_drop_amount = Decimal("15")
        settings.payout.fixed_allowance = Decimal("50")
        settings.kitchen.latitude, settings.kitchen.longitude = 13.05, 80.24
        await settings_service.save_settings_version(db, effective_from=MONTH, settings=settings,
                                                     actor_id=admin.id, reason="Test rates")
        await db.commit()
        return {"admin": admin.id, "d1": d1.id, "d2": d2.id, "c1": c1.id, "c2": c2.id, "plan": plan.id}


async def _activate(db, w, customer="c1"):
    return await subscription_service.activate(db, customer_id=w[customer], plan_id=w["plan"], service_month=MONTH,
                                               actor_id=w["admin"], now=ist(date(2029, 12, 20), 10))


async def _ledger(db, customer_id, entry_type=None):
    q = select(func.coalesce(func.sum(CustomerLedgerEntry.amount), 0)).where(CustomerLedgerEntry.customer_id == customer_id)
    if entry_type:
        q = q.where(CustomerLedgerEntry.entry_type == entry_type)
    return Decimal(await db.scalar(q))


@pytest.mark.asyncio
async def test_subscription_activation_generates_calendar_and_charges_once(world):
    async with SessionLocal() as db:
        await settings_service.set_service_date_exception(db, service_date=date(2030, 1, 26), is_open=False,
                                                          reason="Republic Day", actor_id=world["admin"])
        pv, _ = await subscription_service.preview(db, plan_id=world["plan"], service_month=MONTH)
        assert len(pv.service_dates) == 26  # Jan 2030: 31 days - 4 Sundays - Republic Day
        assert pv.total_slots == 78
        assert pv.per_meal_value_display == Decimal("70.51")

        sub = await _activate(db, world)
        await db.commit()
        slots = await db.scalar(select(func.count()).select_from(SubscriptionMealSlot)
                                .where(SubscriptionMealSlot.subscription_id == sub.id))
        assert slots == 78
        assert await _ledger(db, world["c1"]) == Decimal("5500.00")

        with pytest.raises(Conflict):
            await _activate(db, world)


@pytest.mark.asyncio
async def test_skip_cutoffs_credit_and_restore(world):
    async with SessionLocal() as db:
        sub = await _activate(db, world)
        await db.commit()

        # 08:00 IST: lunch (cutoff 09:00) is on time, breakfast (cutoff 19:00 the day before) is late
        result = await subscription_service.skip_meals(
            db, subscription_id=sub.id, targets=[(SERVICE_DAY, MealWindow.LUNCH), (SERVICE_DAY, MealWindow.BREAKFAST)],
            reason="Customer travelling", actor_id=world["admin"], now=ist(SERVICE_DAY, 8))
        await db.commit()
        assert (result.skipped, result.credit_eligible, result.late) == (2, 1, 1)
        assert sub.total_slots == 81  # 27 service days in Jan 2030 x 3 meals
        assert result.credit_posted == Decimal("67.90")  # 5500 / 81
        assert await _ledger(db, world["c1"], LedgerEntryType.SKIP_CREDIT) == -result.credit_posted

        # Whole day skip the next day, early enough for all three
        nxt = SERVICE_DAY + timedelta(days=1)
        r2 = await subscription_service.skip_meals(db, subscription_id=sub.id, targets=[(nxt, None)],
                                                   reason="Holiday", actor_id=world["admin"], now=ist(SERVICE_DAY, 9))
        await db.commit()
        assert (r2.skipped, r2.credit_eligible) == (3, 3)
        assert await _ledger(db, world["c1"], LedgerEntryType.SKIP_CREDIT) == Decimal("-271.60")  # 5500*4/81

        # Restoring reverses exactly what was credited
        await subscription_service.restore_meals(db, subscription_id=sub.id, targets=[(nxt, None), (SERVICE_DAY, None)],
                                                 reason="Plans changed", actor_id=world["admin"])
        await db.commit()
        assert await _ledger(db, world["c1"], LedgerEntryType.SKIP_CREDIT) == Decimal("0.00")
        assert await db.scalar(select(func.count()).select_from(AuditLog)
                               .where(AuditLog.entity_id == str(sub.id))) == 4

        with pytest.raises(ValidationFailed):
            await subscription_service.skip_meals(db, subscription_id=sub.id, targets=[(SERVICE_DAY, None)],
                                                  reason=" ", actor_id=world["admin"], now=ist(SERVICE_DAY, 6))


@pytest.mark.asyncio
async def test_tasks_shared_inbox_no_duplicates_and_skip_cancels_unstarted(world):
    async with SessionLocal() as db:
        sub = await _activate(db, world)
        order = await one_time_order_service.submit_request(
            db, customer_id=world["c2"], source=OrderSource.CUSTOMER, actor_id=None, idempotency_key="req-1",
            lines=[one_time_order_service.RequestedLine(SERVICE_DAY, MealWindow.LUNCH, 2, "Party meals")])
        again = await one_time_order_service.submit_request(
            db, customer_id=world["c2"], source=OrderSource.CUSTOMER, actor_id=None, idempotency_key="req-1",
            lines=[one_time_order_service.RequestedLine(SERVICE_DAY, MealWindow.LUNCH, 2)])
        assert again.id == order.id
        await db.commit()

        # Pending requests create no tasks
        assert await task_service.generate_tasks(db, SERVICE_DAY) == 3
        line = (await db.execute(select(OneTimeOrderLine).where(OneTimeOrderLine.order_id == order.id))).scalars().one()
        await one_time_order_service.confirm(db, order_id=order.id, unit_prices={line.id: Decimal("150")},
                                             actor_id=world["admin"], now=ist(SERVICE_DAY, 6))
        assert await task_service.generate_tasks(db, SERVICE_DAY) == 1
        assert await task_service.generate_tasks(db, SERVICE_DAY) == 0
        await db.commit()
        assert order.status == OneTimeOrderStatus.CONFIRMED
        assert await _ledger(db, world["c2"], LedgerEntryType.ORDER_CHARGE) == Decimal("300.00")

        # Skip cancels the unstarted lunch task; restore lets a fresh task be generated
        await subscription_service.skip_meals(db, subscription_id=sub.id, targets=[(SERVICE_DAY, MealWindow.LUNCH)],
                                              reason="Sick", actor_id=world["admin"], now=ist(SERVICE_DAY, 7))
        lunch_tasks = (await db.execute(select(DeliveryTask).where(
            DeliveryTask.customer_id == world["c1"], DeliveryTask.meal_window == MealWindow.LUNCH))).scalars().all()
        assert [t.status for t in lunch_tasks] == [TaskStatus.CANCELLED]
        await subscription_service.restore_meals(db, subscription_id=sub.id, targets=[(SERVICE_DAY, MealWindow.LUNCH)],
                                                 reason="Back", actor_id=world["admin"])
        assert await task_service.generate_tasks(db, SERVICE_DAY) == 1
        await db.commit()


@pytest.mark.asyncio
async def test_assignment_accept_decline_and_five_minute_expiry(world):
    async with SessionLocal() as db:
        await _activate(db, world)
        await task_service.generate_tasks(db, SERVICE_DAY)
        tasks = (await db.execute(select(DeliveryTask).where(DeliveryTask.service_date == SERVICE_DAY)
                                  .order_by(DeliveryTask.meal_window))).scalars().all()
        t_break, t_dinner, t_lunch = tasks  # alphabetical: BREAKFAST, DINNER, LUNCH
        t0 = ist(SERVICE_DAY, 5)

        await task_service.assign(db, task_id=t_break.id, driver_id=world["d1"], actor_id=world["admin"], now=t0)
        await task_service.accept(db, task_id=t_break.id, driver_id=world["d1"], now=t0 + timedelta(minutes=2))
        assert t_break.status == TaskStatus.ACCEPTED
        with pytest.raises(NotFound):  # another driver cannot accept it
            await task_service.accept(db, task_id=t_break.id, driver_id=world["d2"], now=t0)

        await task_service.assign(db, task_id=t_lunch.id, driver_id=world["d1"], actor_id=world["admin"], now=t0)
        with pytest.raises(ValidationFailed):
            await task_service.decline(db, task_id=t_lunch.id, driver_id=world["d1"], reason="", now=t0)
        await task_service.decline(db, task_id=t_lunch.id, driver_id=world["d1"], reason="Bike issue", now=t0)
        assert t_lunch.status == TaskStatus.REASSIGNMENT_NEEDED and t_lunch.assigned_driver_id is None

        await task_service.assign(db, task_id=t_dinner.id, driver_id=world["d2"], actor_id=world["admin"], now=t0)
        assert await task_service.expire_overdue_assignments(db, t0 + timedelta(minutes=4)) == 0
        assert await task_service.expire_overdue_assignments(db, t0 + timedelta(minutes=5)) == 1
        assert t_dinner.status == TaskStatus.REASSIGNMENT_NEEDED
        # The task still exists and can be reassigned
        await task_service.assign(db, task_id=t_dinner.id, driver_id=world["d1"], actor_id=world["admin"],
                                  now=t0 + timedelta(minutes=6))
        await db.commit()
        kinds = (await db.execute(select(AdminAlert.kind))).scalars().all()
        assert sorted(kinds) == ["ASSIGNMENT_DECLINED", "ASSIGNMENT_EXPIRED"]

        # Late acceptance of an offer expires it instead
        with pytest.raises(Conflict):
            await task_service.accept(db, task_id=t_dinner.id, driver_id=world["d1"], now=t0 + timedelta(minutes=30))


async def _lunch_trip(db, w, maps):
    """Two lunch stops for driver d1, accepted and started."""
    await _activate(db, w, "c1")
    await _activate(db, w, "c2")
    await task_service.generate_tasks(db, SERVICE_DAY)
    lunch = (await db.execute(select(DeliveryTask).where(DeliveryTask.service_date == SERVICE_DAY,
                                                         DeliveryTask.meal_window == MealWindow.LUNCH)
                              .order_by(DeliveryTask.customer_id))).scalars().all()
    by_customer = {t.customer_id: t for t in lunch}
    order = [by_customer[w["c2"]], by_customer[w["c1"]]]  # admin chooses Bala first
    t0 = ist(SERVICE_DAY, 10)
    for t in order:
        await task_service.assign(db, task_id=t.id, driver_id=w["d1"], actor_id=w["admin"], now=t0)
        await task_service.accept(db, task_id=t.id, driver_id=w["d1"], now=t0)
    trip = await task_service.set_stop_sequence(db, driver_id=w["d1"], service_date=SERVICE_DAY,
                                                meal_window=MealWindow.LUNCH, task_ids=[t.id for t in order],
                                                actor_id=w["admin"])
    await trip_service.start_trip(db, trip_id=trip.id, driver_id=w["d1"], now=ist(SERVICE_DAY, 11, 30))
    return trip, order


@pytest.mark.asyncio
async def test_trip_fees_earnings_and_finalization(world):
    async with SessionLocal() as db:
        maps = FakeMaps(legs=[3.2, 1.1], return_leg=4.0)
        trip, (first, second) = await _lunch_trip(db, world, maps)

        with pytest.raises(Conflict):  # cannot end with undelivered tasks
            await trip_service.end_trip(db, trip_id=trip.id, driver_id=world["d1"], now=ist(SERVICE_DAY, 12), provider=maps)

        await trip_service.record_outcome(db, task_id=first.id, driver_id=world["d1"], outcome=TaskStatus.DELIVERED,
                                          now=ist(SERVICE_DAY, 12), note="Gate")
        # Repeating delivered changes nothing
        await trip_service.record_outcome(db, task_id=first.id, driver_id=world["d1"], outcome=TaskStatus.DELIVERED,
                                          now=ist(SERVICE_DAY, 12, 1))
        with pytest.raises(ValidationFailed):
            await trip_service.record_outcome(db, task_id=second.id, driver_id=world["d1"], outcome=TaskStatus.FAILED,
                                              now=ist(SERVICE_DAY, 12, 20))
        await trip_service.record_outcome(db, task_id=second.id, driver_id=world["d1"], outcome=TaskStatus.FAILED,
                                          reason="Customer unavailable", now=ist(SERVICE_DAY, 12, 20))
        with pytest.raises(NotFound):  # other driver cannot touch it
            await trip_service.record_outcome(db, task_id=first.id, driver_id=world["d2"],
                                              outcome=TaskStatus.DELIVERED, now=ist(SERVICE_DAY, 12))

        await trip_service.end_trip(db, trip_id=trip.id, driver_id=world["d1"], now=ist(SERVICE_DAY, 12, 40), provider=maps)
        await db.commit()
        assert trip.status == TripStatus.ENDED and trip.distance_status == DistanceStatus.CALCULATED
        assert trip.payable_km == Decimal("4.300")  # return leg excluded by default
        assert maps.calls[0][0] == (13.05, 80.24)

        # Customer fees: Bala (first leg 3.2 km) delivered; Asha failed, so not charged
        assert await _ledger(db, world["c2"], LedgerEntryType.DELIVERY_FEE) == Decimal("32.00")
        assert await _ledger(db, world["c1"], LedgerEntryType.DELIVERY_FEE) == Decimal("0.00")

        summary = await earnings_service.calculate_day(db, driver_id=world["d1"], service_date=SERVICE_DAY)
        lines = await earnings_service.lines_for_day(db, summary.id)
        amounts = {l.code: l.amount for l in lines}
        assert amounts[EarningCode.PER_KM] == Decimal("17.20")       # 4.3 km × 4
        assert amounts[EarningCode.PER_DROP] == Decimal("15.00")     # one successful drop only
        assert amounts[EarningCode.FIXED_ALLOWANCE] == Decimal("50.00")
        assert summary.total_amount == Decimal("82.20")

        final = await earnings_service.finalize_day(db, driver_id=world["d1"], service_date=SERVICE_DAY,
                                                    actor_id=world["admin"], now=ist(SERVICE_DAY, 22))
        await db.commit()
        assert final.status == DaySummaryStatus.FINALIZED
        assert final.policy_snapshot["per_km_rate"] == "4"

        # A later settings change does not rewrite the finalized day
        newer = BusinessSettings()
        newer.payout.per_km_rate = Decimal("100")
        await settings_service.save_settings_version(db, effective_from=SERVICE_DAY, settings=newer,
                                                     actor_id=world["admin"], reason="Rate change")
        again = await earnings_service.calculate_day(db, driver_id=world["d1"], service_date=SERVICE_DAY)
        assert again.total_amount == Decimal("82.20")

        # Corrections after finalization are itemized adjustments; distances are locked
        with pytest.raises(Conflict):
            await trip_service.enter_manual_distances(db, trip_id=trip.id, stop_legs_km=[Decimal("1"), Decimal("1")],
                                                      return_leg_km=Decimal("1"), reason="fix", actor_id=world["admin"])
        await earnings_service.add_adjustment(db, driver_id=world["d1"], service_date=SERVICE_DAY,
                                              amount=Decimal("-10"), reason="Fuel advance recovered",
                                              actor_id=world["admin"])
        await db.commit()
        assert again.total_amount == Decimal("72.20")


@pytest.mark.asyncio
async def test_maps_failure_requires_audited_manual_distance(world):
    async with SessionLocal() as db:
        trip, (first, second) = await _lunch_trip(db, world, None)
        for t in (first, second):
            await trip_service.record_outcome(db, task_id=t.id, driver_id=world["d1"], outcome=TaskStatus.DELIVERED,
                                              now=ist(SERVICE_DAY, 12))
        await trip_service.end_trip(db, trip_id=trip.id, driver_id=world["d1"], now=ist(SERVICE_DAY, 12, 30),
                                    provider=BrokenMaps())
        assert trip.distance_status == DistanceStatus.NEEDS_MANUAL_ENTRY
        with pytest.raises(Conflict):
            await earnings_service.finalize_day(db, driver_id=world["d1"], service_date=SERVICE_DAY,
                                                actor_id=world["admin"], now=ist(SERVICE_DAY, 22))

        await trip_service.enter_manual_distances(db, trip_id=trip.id, stop_legs_km=[Decimal("2.5"), Decimal("1.5")],
                                                  return_leg_km=Decimal("3"), reason="Maps returned no route",
                                                  actor_id=world["admin"])
        # Correcting again posts only the difference in delivery fees
        await trip_service.enter_manual_distances(db, trip_id=trip.id, stop_legs_km=[Decimal("2.0"), Decimal("1.5")],
                                                  return_leg_km=Decimal("3"), reason="Odometer check",
                                                  actor_id=world["admin"])
        await db.commit()
        legs = (await db.execute(select(RouteLeg).where(RouteLeg.trip_id == trip.id))).scalars().all()
        assert {l.source.value for l in legs} == {"MANUAL"}
        assert await _ledger(db, world["c2"], LedgerEntryType.DELIVERY_FEE) == Decimal("20.00")
        assert await _ledger(db, world["c1"], LedgerEntryType.DELIVERY_FEE) == Decimal("15.00")
        await earnings_service.finalize_day(db, driver_id=world["d1"], service_date=SERVICE_DAY,
                                            actor_id=world["admin"], now=ist(SERVICE_DAY, 22))


@pytest.mark.asyncio
async def test_payments_are_idempotent_and_allocation_is_manual(world):
    async with SessionLocal() as db:
        sub = await _activate(db, world)
        kwargs = dict(customer_id=world["c1"], method=PaymentMethod.UPI, amount=Decimal("2000"),
                      received_at=ist(SERVICE_DAY, 9), idempotency_key="upi-123", actor_id=world["admin"],
                      reference="UPI-REF-1",
                      allocations=[payment_service.Allocation(Decimal("2000"), subscription_id=sub.id)])
        p1 = await payment_service.record_payment(db, **kwargs)
        p2 = await payment_service.record_payment(db, **kwargs)
        assert p1.id == p2.id
        assert await payment_service.customer_balance(db, world["c1"]) == Decimal("3500.00")  # partial payment

        await payment_service.record_payment(db, customer_id=world["c1"], method=PaymentMethod.CASH,
                                             amount=Decimal("4000"), received_at=ist(SERVICE_DAY, 10),
                                             idempotency_key="cash-1", actor_id=world["admin"])
        assert await payment_service.customer_balance(db, world["c1"]) == Decimal("-500.00")  # advance

        with pytest.raises(ValidationFailed):
            await payment_service.record_payment(
                db, customer_id=world["c2"], method=PaymentMethod.CASH, amount=Decimal("10"),
                received_at=ist(SERVICE_DAY, 10), idempotency_key="cash-2", actor_id=world["admin"],
                allocations=[payment_service.Allocation(Decimal("10"), subscription_id=sub.id)])

        await payment_service.manual_adjustment(db, customer_id=world["c1"], amount=Decimal("-70.51"),
                                                reason="Goodwill for late skip", actor_id=world["admin"])
        assert await payment_service.customer_balance(db, world["c1"]) == Decimal("-570.51")
        await db.commit()
