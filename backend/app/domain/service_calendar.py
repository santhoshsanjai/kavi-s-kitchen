import calendar
from datetime import date
from typing import Iterable, List, Set

# Python weekday numbers: Monday=0 ... Sunday=6
DEFAULT_SERVICE_WEEKDAYS = frozenset({0, 1, 2, 3, 4, 5})  # Monday-Saturday


def month_start(any_day: date) -> date:
    return any_day.replace(day=1)


def month_dates(service_month: date) -> List[date]:
    _, days = calendar.monthrange(service_month.year, service_month.month)
    return [date(service_month.year, service_month.month, d) for d in range(1, days + 1)]


def generate_service_dates(
    service_month: date,
    service_weekdays: Iterable[int] = DEFAULT_SERVICE_WEEKDAYS,
    closed_dates: Iterable[date] = (),
    open_dates: Iterable[date] = (),
) -> List[date]:
    """
    Actual service dates for a month: configured weekdays, minus closed dates (holidays),
    plus explicitly opened dates (admin override of a non-service day). A date that is both
    opened and closed stays closed.
    """
    weekdays: Set[int] = set(service_weekdays)
    closed = set(closed_dates)
    opened = set(open_dates)
    result = []
    for d in month_dates(service_month):
        if d in closed:
            continue
        if d.weekday() in weekdays or d in opened:
            result.append(d)
    return result
