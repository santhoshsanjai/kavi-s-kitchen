import uuid
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import business_today
from app.domain.service_calendar import generate_service_dates, month_dates
from app.models.settings import ServiceDateException, SettingsVersion
from app.schemas.settings import BusinessSettings
from app.services.common import audit, require_reason
from app.services.errors import Conflict, ValidationFailed


async def get_settings(db: AsyncSession, on_date: date) -> Tuple[Optional[SettingsVersion], BusinessSettings]:
    """Settings in force on a date. Before any version is saved, built-in defaults apply."""
    version = (await db.execute(
        select(SettingsVersion).where(SettingsVersion.effective_from <= on_date)
        .order_by(SettingsVersion.effective_from.desc()).limit(1)
    )).scalars().first()
    if version is None:
        return None, BusinessSettings()
    return version, BusinessSettings.model_validate(version.data)


async def save_settings_version(db: AsyncSession, *, effective_from: date, settings: BusinessSettings,
                                actor_id: uuid.UUID, reason: str) -> SettingsVersion:
    """New rules apply from effective_from onward. Past dates keep the rules they were calculated with."""
    reason = require_reason(reason, "Changing settings")
    if effective_from < business_today():
        raise ValidationFailed("Settings changes cannot take effect in the past")
    existing = (await db.execute(
        select(SettingsVersion).where(SettingsVersion.effective_from == effective_from)
    )).scalars().first()
    if existing is not None:
        raise Conflict("A settings version already starts on that date")
    version = SettingsVersion(effective_from=effective_from, data=settings.model_dump(mode="json"),
                              reason=reason, created_by_id=actor_id)
    db.add(version)
    await db.flush()
    audit(db, actor_id, "settings.version_created", "settings_version", version.id, reason,
          {"effective_from": effective_from.isoformat()})
    return version


async def set_service_date_exception(db: AsyncSession, *, service_date: date, is_open: bool, reason: str,
                                     actor_id: uuid.UUID) -> ServiceDateException:
    reason = require_reason(reason, "A holiday or service override")
    _, settings = await get_settings(db, service_date)
    if is_open and not settings.calendar.allow_open_overrides:
        raise ValidationFailed("Opening service on a non-service day is not enabled in settings")
    row = (await db.execute(
        select(ServiceDateException).where(ServiceDateException.service_date == service_date)
    )).scalars().first()
    if row is None:
        row = ServiceDateException(service_date=service_date, is_open=is_open, reason=reason, created_by_id=actor_id)
        db.add(row)
    else:
        row.is_open, row.reason, row.created_by_id = is_open, reason, actor_id
    await db.flush()
    audit(db, actor_id, "calendar.exception_set", "service_date_exception", row.id, reason,
          {"date": service_date.isoformat(), "is_open": is_open})
    return row


async def service_dates_for_month(db: AsyncSession, service_month: date, settings: BusinessSettings) -> List[date]:
    days = month_dates(service_month)
    exceptions = (await db.execute(
        select(ServiceDateException).where(ServiceDateException.service_date.between(days[0], days[-1]))
    )).scalars().all()
    return generate_service_dates(
        service_month,
        service_weekdays=settings.calendar.service_weekdays,
        closed_dates=[e.service_date for e in exceptions if not e.is_open],
        open_dates=[e.service_date for e in exceptions if e.is_open] if settings.calendar.allow_open_overrides else [],
    )
