import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.meal_windows import MealWindow
from app.models._types import str_enum


class OneTimeOrderStatus(str, enum.Enum):
    REQUEST_PENDING = "REQUEST_PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderSource(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class OneTimeOrder(UUIDPrimaryKey, Timestamps, Base):
    """A customer request or admin inquiry. Only CONFIRMED orders produce delivery tasks."""
    __tablename__ = "one_time_orders"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    enquiry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("enquiries.id"))
    source: Mapped[OrderSource] = mapped_column(str_enum(OrderSource, "order_source"), nullable=False)
    status: Mapped[OneTimeOrderStatus] = mapped_column(str_enum(OneTimeOrderStatus, "one_time_order_status"), nullable=False, index=True)
    delivery_address: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    request_notes: Mapped[Optional[str]] = mapped_column(Text)
    # Set by admin on confirmation
    estimated_delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    # Client-supplied key so a double-tapped submit creates one request
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(80), unique=True)


class OneTimeOrderLine(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "one_time_order_lines"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("one_time_orders.id", ondelete="CASCADE"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_window: Mapped[MealWindow] = mapped_column(str_enum(MealWindow, "meal_window"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[Optional[str]] = mapped_column(Text)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))  # confirmed by admin
