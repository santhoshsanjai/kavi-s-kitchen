from decimal import Decimal

import pytest

from app.domain.money import RoundingPolicy, round_money
from app.domain.proration import cumulative_skip_credit, per_meal_value


def test_spec_example_per_meal_value():
    value = per_meal_value(Decimal("5500"), 26 * 3)
    assert round_money(value) == Decimal("70.51")
    assert str(value).startswith("70.512820")


def test_fewer_included_slots_use_actual_count():
    # Lunch-only plan over 27 service days
    assert round_money(per_meal_value(Decimal("2799"), 27)) == Decimal("103.67")


def test_total_policy_has_no_cumulative_drift():
    # Skipping every slot one by one must credit exactly the plan amount
    plan, slots = Decimal("5500"), 78
    posted = Decimal("0")
    for n in range(1, slots + 1):
        cumulative = cumulative_skip_credit(plan, slots, n, RoundingPolicy.TOTAL)
        posted += cumulative - cumulative_skip_credit(plan, slots, n - 1, RoundingPolicy.TOTAL)
    assert posted == Decimal("5500.00")


def test_per_slot_policy_rounds_each_slot():
    assert cumulative_skip_credit(Decimal("5500"), 78, 3, RoundingPolicy.PER_SLOT) == Decimal("211.53")
    assert cumulative_skip_credit(Decimal("5500"), 78, 3, RoundingPolicy.TOTAL) == Decimal("211.54")


def test_invalid_counts_rejected():
    with pytest.raises(ValueError):
        per_meal_value(Decimal("5500"), 0)
    with pytest.raises(ValueError):
        cumulative_skip_credit(Decimal("5500"), 10, 11, RoundingPolicy.TOTAL)
