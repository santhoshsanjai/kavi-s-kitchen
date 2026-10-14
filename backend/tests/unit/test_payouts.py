from decimal import Decimal

from app.domain.payouts import (
    DropUnit, EarningCode, FixedAllowancePeriod, PayoutPolicy,
    count_drops, day_fixed_allowance, total, trip_earning_lines, trip_kilometres,
)


def test_return_leg_only_when_included():
    legs = [Decimal("3.2"), Decimal("1.1"), Decimal("0.7")]
    assert trip_kilometres(legs, Decimal("4.0"), include_return_leg=False) == Decimal("5.0")
    assert trip_kilometres(legs, Decimal("4.0"), include_return_leg=True) == Decimal("9.0")


def test_drop_units():
    delivered = [("t1", "custA"), ("t2", "custA"), ("t3", "custB")]
    assert count_drops(delivered, DropUnit.PER_TASK) == 3
    assert count_drops(delivered, DropUnit.PER_STOP) == 2


def test_trip_and_day_earnings():
    policy = PayoutPolicy(
        per_km_rate=Decimal("4"), fixed_allowance=Decimal("50"),
        fixed_allowance_period=FixedAllowancePeriod.PER_DAY, per_drop_amount=Decimal("15"),
    )
    breakfast = trip_earning_lines(policy, Decimal("9.25"), drops=4)
    lunch = trip_earning_lines(policy, Decimal("6"), drops=3)
    fixed = day_fixed_allowance(policy, completed_trips=2)
    assert [l.amount for l in breakfast] == [Decimal("37.00"), Decimal("60.00")]
    assert len(fixed) == 1 and fixed[0].code == EarningCode.FIXED_ALLOWANCE
    assert total(breakfast + lunch + fixed) == Decimal("37.00") + Decimal("60.00") + Decimal("24.00") + Decimal("45.00") + Decimal("50.00")


def test_per_trip_allowance_and_no_allowance_without_trips():
    policy = PayoutPolicy(fixed_allowance=Decimal("30"), fixed_allowance_period=FixedAllowancePeriod.PER_TRIP)
    assert any(l.code == EarningCode.FIXED_ALLOWANCE for l in trip_earning_lines(policy, 0, 0))
    assert day_fixed_allowance(policy, 2) == []
    assert day_fixed_allowance(PayoutPolicy(fixed_allowance=Decimal("30")), 0) == []
