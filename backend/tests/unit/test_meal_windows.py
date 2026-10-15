from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.domain.meal_windows import is_skip_on_time

IST = ZoneInfo("Asia/Kolkata")


def test_skip_cutoff_is_per_window_in_ist():
    service_day = date(2026, 10, 15)
    lunch_start = time(12, 0)
    # 3 hour cutoff: last on-time skip is 09:00 IST
    assert is_skip_on_time(datetime(2026, 10, 15, 9, 0, tzinfo=IST), service_day, lunch_start, 180, IST)
    assert not is_skip_on_time(datetime(2026, 10, 15, 9, 1, tzinfo=IST), service_day, lunch_start, 180, IST)


def test_utc_now_is_compared_correctly():
    from datetime import timezone
    # 03:29 UTC = 08:59 IST
    assert is_skip_on_time(datetime(2026, 10, 15, 3, 29, tzinfo=timezone.utc), date(2026, 10, 15), time(12), 180, IST)


def test_naive_now_rejected():
    with pytest.raises(ValueError):
        is_skip_on_time(datetime(2026, 10, 15, 9), date(2026, 10, 15), time(12), 180, IST)
