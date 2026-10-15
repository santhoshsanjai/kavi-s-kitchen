from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Hashable, List

from app.domain.money import round_money, to_decimal


@dataclass(frozen=True)
class RouteStop:
    """One customer stop in admin-defined order. leg_km is the distance from the previous stop
    (from the kitchen for the first stop)."""
    key: Hashable
    leg_km: Decimal
    delivered: bool


def customer_delivery_charges(stops: List[RouteStop], rate_per_km, minimum_fee=Decimal("0")) -> Dict[Hashable, Decimal]:
    """
    Charge per delivered stop = its route leg km × rate, at least minimum_fee, rounded.
    Undelivered stops are not charged. The driver's return leg is never passed in here,
    so it is never allocated to a customer.
    """
    rate = to_decimal(rate_per_km)
    minimum = to_decimal(minimum_fee)
    charges: Dict[Hashable, Decimal] = {}
    for stop in stops:
        if not stop.delivered:
            charges[stop.key] = Decimal("0.00")
            continue
        charges[stop.key] = round_money(max(to_decimal(stop.leg_km) * rate, minimum))
    return charges
