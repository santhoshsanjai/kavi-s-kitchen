from datetime import date

from app.domain.service_calendar import generate_service_dates


def test_october_2026_excludes_sundays():
    dates = generate_service_dates(date(2026, 10, 1))
    assert len(dates) == 27  # 31 days - 4 Sundays
    assert all(d.weekday() != 6 for d in dates)


def test_holidays_are_excluded_and_month_is_not_forced_to_26_days():
    diwali = date(2026, 11, 9)  # a Monday
    dates = generate_service_dates(date(2026, 11, 1), closed_dates=[diwali])
    assert diwali not in dates
    assert len(dates) == 24  # 30 days - 5 Sundays - 1 holiday


def test_open_override_adds_a_sunday_but_closed_wins():
    sunday = date(2026, 10, 4)
    assert sunday in generate_service_dates(date(2026, 10, 1), open_dates=[sunday])
    assert sunday not in generate_service_dates(date(2026, 10, 1), open_dates=[sunday], closed_dates=[sunday])


def test_configurable_service_weekdays():
    weekdays_only = generate_service_dates(date(2026, 10, 1), service_weekdays={0, 1, 2, 3, 4})
    assert len(weekdays_only) == 22
