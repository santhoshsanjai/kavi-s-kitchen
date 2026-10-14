from decimal import Decimal, ROUND_HALF_UP, localcontext
from enum import Enum

CENT = Decimal("0.01")


class RoundingPolicy(str, Enum):
    # Round only the final amount of a calculation (no cumulative drift). Default.
    TOTAL = "TOTAL"
    # Round each meal slot's value first, then multiply.
    PER_SLOT = "PER_SLOT"


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        # Go through str so 70.1 stays 70.1 instead of its binary approximation
        return Decimal(str(value))
    return Decimal(value)


def round_money(value) -> Decimal:
    """The single currency rounding rule: 2 decimal places, half up."""
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def exact_div(numerator, denominator) -> Decimal:
    """High precision division for intermediate values that are rounded later."""
    with localcontext() as ctx:
        ctx.prec = 34
        return to_decimal(numerator) / to_decimal(denominator)
