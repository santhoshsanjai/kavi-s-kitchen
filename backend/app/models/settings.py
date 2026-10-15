import uuid
from datetime import date
from typing import Any, Dict, Optional
from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey


class SettingsVersion(UUIDPrimaryKey, Timestamps, Base):
    """Effective-dated business settings. The version in force on a date is the latest effective_from <= date."""
    __tablename__ = "settings_versions"

    effective_from: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class ServiceDateException(UUIDPrimaryKey, Timestamps, Base):
    """A holiday (is_open=False) or an admin-opened non-service day (is_open=True)."""
    __tablename__ = "service_date_exceptions"

    service_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    is_open: Mapped[bool] = mapped_column(nullable=False, default=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
