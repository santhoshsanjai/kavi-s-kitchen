"""
Business settings that affect billing or payout. Stored as effective-dated versions
(settings_versions table) so historical calculations keep the rules they were made with.

Defaults marked OPEN DECISION follow the spec's Section 14 open questions and must be
confirmed by the owner before production use. Money defaults are 0 so nothing is charged
or paid until the owner sets real values.
"""
from datetime import time
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.meal_windows import MealWindow
from app.domain.money import RoundingPolicy
from app.domain.payouts import DropUnit, FixedAllowancePeriod, PayoutPolicy


class MealWindowSettings(BaseModel):
    start: time
    end: time
    # Skip earns automatic credit only if made at least this many minutes before the window starts
    skip_cutoff_minutes: int = Field(ge=0)


class CalendarSettings(BaseModel):
    service_weekdays: List[int] = Field(default=[0, 1, 2, 3, 4, 5], description="0=Monday ... 6=Sunday")
    # OPEN DECISION #12: may admins open service on a Sunday/holiday? Off until confirmed.
    allow_open_overrides: bool = False


class BillingSettings(BaseModel):
    # OPEN DECISION #3: round only final totals (no drift) vs. per meal slot
    rounding_policy: RoundingPolicy = RoundingPolicy.TOTAL


class DeliveryFeeSettings(BaseModel):
    # OPEN DECISION #1: rate and minimum not yet set
    customer_rate_per_km: Decimal = Decimal("0")
    minimum_fee: Decimal = Decimal("0")


class PayoutSettings(BaseModel):
    per_km_rate: Decimal = Decimal("0")
    fixed_allowance: Decimal = Decimal("0")
    # OPEN DECISION #4: per trip or per day. Allowance stays 0 until confirmed.
    fixed_allowance_period: FixedAllowancePeriod = FixedAllowancePeriod.PER_DAY
    per_drop_amount: Decimal = Decimal("0")
    include_return_leg: bool = False
    # OPEN DECISION #5: one drop per delivered task (spec's current assumption) or per stop
    drop_unit: DropUnit = DropUnit.PER_TASK

    def policy(self) -> PayoutPolicy:
        return PayoutPolicy(**self.model_dump())


class KitchenSettings(BaseModel):
    """Trip origin and return point. Route distances cannot be calculated until this is set."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class OperationsSettings(BaseModel):
    assignment_timeout_minutes: int = Field(default=5, ge=1)
    # OPEN DECISION #11: may a driver end a trip with unattempted tasks if they give a reason?
    allow_end_trip_with_unattempted: bool = False
    notification_refresh_seconds: int = Field(default=60, ge=10)


class BusinessSettings(BaseModel):
    meal_windows: Dict[MealWindow, MealWindowSettings] = Field(default_factory=lambda: {
        MealWindow.BREAKFAST: MealWindowSettings(start=time(7, 0), end=time(9, 0), skip_cutoff_minutes=12 * 60),
        MealWindow.LUNCH: MealWindowSettings(start=time(12, 0), end=time(14, 0), skip_cutoff_minutes=3 * 60),
        MealWindow.DINNER: MealWindowSettings(start=time(19, 0), end=time(21, 0), skip_cutoff_minutes=3 * 60),
    })
    calendar: CalendarSettings = Field(default_factory=CalendarSettings)
    billing: BillingSettings = Field(default_factory=BillingSettings)
    delivery_fees: DeliveryFeeSettings = Field(default_factory=DeliveryFeeSettings)
    payout: PayoutSettings = Field(default_factory=PayoutSettings)
    operations: OperationsSettings = Field(default_factory=OperationsSettings)
    kitchen: KitchenSettings = Field(default_factory=KitchenSettings)
