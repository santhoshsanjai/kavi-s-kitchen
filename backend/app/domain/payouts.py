from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Hashable, Iterable, List, Optional, Tuple

from app.domain.money import round_money, to_decimal


class FixedAllowancePeriod(str, Enum):
    PER_TRIP = "PER_TRIP"
    PER_DAY = "PER_DAY"


class DropUnit(str, Enum):
    # One drop per successfully delivered task (one meal/order line). Spec's current assumption.
    PER_TASK = "PER_TASK"
    # One drop per customer stop, however many tasks were delivered there.
    PER_STOP = "PER_STOP"


class EarningCode(str, Enum):
    PER_KM = "PER_KM"
    FIXED_ALLOWANCE = "FIXED_ALLOWANCE"
    PER_DROP = "PER_DROP"
    ADJUSTMENT = "ADJUSTMENT"


@dataclass(frozen=True)
class PayoutPolicy:
    per_km_rate: Decimal = Decimal("0")
    fixed_allowance: Decimal = Decimal("0")
    fixed_allowance_period: FixedAllowancePeriod = FixedAllowancePeriod.PER_DAY
    per_drop_amount: Decimal = Decimal("0")
    include_return_leg: bool = False
    drop_unit: DropUnit = DropUnit.PER_TASK


@dataclass(frozen=True)
class EarningLine:
    code: EarningCode
    quantity: Decimal
    rate: Decimal
    amount: Decimal
    description: str = ""


def trip_kilometres(stop_legs_km: Iterable, return_leg_km: Optional[Decimal], include_return_leg: bool) -> Decimal:
    """Sum of route legs for the stop sequence, plus the return leg only when the policy includes it."""
    total = sum((to_decimal(km) for km in stop_legs_km), Decimal("0"))
    if include_return_leg and return_leg_km is not None:
        total += to_decimal(return_leg_km)
    return total


def count_drops(delivered: Iterable[Tuple[Hashable, Hashable]], unit: DropUnit) -> int:
    """
    delivered: (task_key, stop_key) for each successfully DELIVERED task only.
    Failed and partial deliveries must not be passed in; they never earn the per-drop amount.
    """
    pairs = list(delivered)
    if unit == DropUnit.PER_STOP:
        return len({stop for _, stop in pairs})
    return len({task for task, _ in pairs})


def trip_earning_lines(policy: PayoutPolicy, kilometres, drops: int) -> List[EarningLine]:
    km = to_decimal(kilometres)
    lines = [
        EarningLine(EarningCode.PER_KM, km, policy.per_km_rate, round_money(km * policy.per_km_rate),
                    "Route distance (Google Maps estimate unless marked manual)"),
        EarningLine(EarningCode.PER_DROP, Decimal(drops), policy.per_drop_amount,
                    round_money(drops * to_decimal(policy.per_drop_amount)), "Successful drops"),
    ]
    if policy.fixed_allowance_period == FixedAllowancePeriod.PER_TRIP and policy.fixed_allowance:
        lines.append(EarningLine(EarningCode.FIXED_ALLOWANCE, Decimal(1), policy.fixed_allowance,
                                 round_money(policy.fixed_allowance), "Fixed allowance (per trip)"))
    return lines


def day_fixed_allowance(policy: PayoutPolicy, completed_trips: int) -> List[EarningLine]:
    if policy.fixed_allowance_period != FixedAllowancePeriod.PER_DAY or not policy.fixed_allowance:
        return []
    if completed_trips == 0:
        return []
    return [EarningLine(EarningCode.FIXED_ALLOWANCE, Decimal(1), policy.fixed_allowance,
                        round_money(policy.fixed_allowance), "Fixed allowance (per day)")]


def total(lines: Iterable[EarningLine]) -> Decimal:
    return round_money(sum((line.amount for line in lines), Decimal("0")))
