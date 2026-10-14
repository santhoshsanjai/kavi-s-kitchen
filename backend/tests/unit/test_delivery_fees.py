from decimal import Decimal

from app.domain.delivery_fees import RouteStop, customer_delivery_charges


def test_each_stop_pays_for_its_own_leg_and_undelivered_pays_nothing():
    stops = [
        RouteStop("first", Decimal("3.2"), True),     # kitchen -> first stop
        RouteStop("second", Decimal("1.15"), False),  # failed: not charged
        RouteStop("third", Decimal("0.8"), True),     # leg from second stop
    ]
    charges = customer_delivery_charges(stops, rate_per_km=Decimal("10"))
    assert charges == {"first": Decimal("32.00"), "second": Decimal("0.00"), "third": Decimal("8.00")}


def test_minimum_fee_applies_only_to_delivered_stops():
    stops = [RouteStop("a", Decimal("0.5"), True), RouteStop("b", Decimal("0.5"), False)]
    charges = customer_delivery_charges(stops, Decimal("10"), minimum_fee=Decimal("20"))
    assert charges == {"a": Decimal("20.00"), "b": Decimal("0.00")}
