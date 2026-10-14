import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.payouts import EarningCode
from app.models._types import str_enum


class DaySummaryStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    FINALIZED = "FINALIZED"


class DriverDaySummary(UUIDPrimaryKey, Timestamps, Base):
    """A driver's earnings for a date. Finalized summaries keep the policy snapshot they were calculated with."""
    __tablename__ = "driver_day_summaries"
    __table_args__ = (UniqueConstraint("driver_id", "service_date"),)

    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DaySummaryStatus] = mapped_column(str_enum(DaySummaryStatus, "day_summary_status"), nullable=False)
    settings_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("settings_versions.id"))
    policy_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finalized_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class DriverEarningLine(UUIDPrimaryKey, Base):
    __tablename__ = "driver_earning_lines"

    summary_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("driver_day_summaries.id", ondelete="CASCADE"), nullable=False, index=True)
    trip_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_trips.id"))
    code: Mapped[EarningCode] = mapped_column(str_enum(EarningCode, "earning_code"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    # Adjustments only: who approved it and why
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
