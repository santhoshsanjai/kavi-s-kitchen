from datetime import date, datetime, time, timedelta
from enum import Enum
from zoneinfo import ZoneInfo


class MealWindow(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


MEAL_WINDOW_ORDER = [MealWindow.BREAKFAST, MealWindow.LUNCH, MealWindow.DINNER]


def skip_cutoff_at(service_date: date, window_start: time, cutoff_minutes_before: int, tz: ZoneInfo) -> datetime:
    """The last moment a skip for this meal still earns automatic credit."""
    return datetime.combine(service_date, window_start, tzinfo=tz) - timedelta(minutes=cutoff_minutes_before)


def is_skip_on_time(
    now: datetime, service_date: date, window_start: time, cutoff_minutes_before: int, tz: ZoneInfo
) -> bool:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now <= skip_cutoff_at(service_date, window_start, cutoff_minutes_before, tz)
