from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from app.core.config import settings

BUSINESS_TZ = ZoneInfo(settings.business_timezone)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def business_today() -> date:
    """Today's date in the business timezone (Asia/Kolkata), not UTC."""
    return datetime.now(BUSINESS_TZ).date()


def parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())
