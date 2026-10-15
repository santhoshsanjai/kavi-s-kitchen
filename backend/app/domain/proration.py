from decimal import Decimal

from app.domain.money import RoundingPolicy, exact_div, round_money, to_decimal


def per_meal_value(plan_amount, total_slots: int) -> Decimal:
    """Monthly plan amount ÷ included meal slots in the generated service month (unrounded)."""
    if total_slots <= 0:
        raise ValueError("A subscription month must include at least one meal slot")
    return exact_div(plan_amount, total_slots)


def cumulative_skip_credit(plan_amount, total_slots: int, eligible_skipped: int, policy: RoundingPolicy) -> Decimal:
    """
    Total automatic credit for a subscription month with `eligible_skipped` on-time skips.
    Services post the difference between the new and the previously posted cumulative credit,
    so repeated skip/restore operations never accumulate rounding drift.
    """
    if eligible_skipped < 0 or eligible_skipped > total_slots:
        raise ValueError("Skipped slot count must be between 0 and the month's slot count")
    if policy == RoundingPolicy.PER_SLOT:
        return round_money(per_meal_value(plan_amount, total_slots)) * eligible_skipped
    return round_money(to_decimal(plan_amount) * eligible_skipped / total_slots)
