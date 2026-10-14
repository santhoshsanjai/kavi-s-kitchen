import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.meal_windows import MealWindow
from app.models._types import str_enum


class PlanRateVersion(UUIDPrimaryKey, Timestamps, Base):
    """Price and included meals of a plan from a date onward. Plan price edits create a new version."""
    __tablename__ = "plan_rate_versions"
    __table_args__ = (UniqueConstraint("plan_id", "effective_from"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    included_meals: Mapped[List[str]] = mapped_column(JSONB, nullable=False)


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class Subscription(UUIDPrimaryKey, Timestamps, Base):
    """One customer's plan for one service month. Amounts are snapshots taken at activation."""
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("uq_subscriptions_customer_month_active", "customer_id", "service_month", unique=True,
              postgresql_where=text("status <> 'CANCELLED'")),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="RESTRICT"), nullable=False)
    plan_rate_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plan_rate_versions.id"), nullable=False)
    settings_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("settings_versions.id"))
    service_month: Mapped[date] = mapped_column(Date, nullable=False)  # first day of month
    status: Mapped[SubscriptionStatus] = mapped_column(str_enum(SubscriptionStatus, "subscription_status"), nullable=False)
    plan_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    included_meals: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    service_days: Mapped[int] = mapped_column(Integer, nullable=False)
    total_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    # Unrounded per-meal value kept for display and audit; credits are computed from plan_amount/total_slots
    per_meal_value: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    credited_skip_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class SlotStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    SKIPPED = "SKIPPED"


class SubscriptionMealSlot(UUIDPrimaryKey, Timestamps, Base):
    """An included meal on a service date. Distinct from the delivery task that fulfils it."""
    __tablename__ = "subscription_meal_slots"
    __table_args__ = (UniqueConstraint("subscription_id", "service_date", "meal_window"),
                      Index("ix_slots_date_window", "service_date", "meal_window"))

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_window: Mapped[MealWindow] = mapped_column(str_enum(MealWindow, "meal_window"), nullable=False)
    status: Mapped[SlotStatus] = mapped_column(str_enum(SlotStatus, "slot_status"), nullable=False, default=SlotStatus.SCHEDULED)
    skip_credit_eligible: Mapped[Optional[bool]] = mapped_column(Boolean)
    skip_reason: Mapped[Optional[str]] = mapped_column(Text)
    skipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    skipped_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
