import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models._types import ev, money, str_enum
from app.schemas.customer import DietType, MealSession, SpiceLevel
from app.schemas.order import OrderStatus, OrderType


class Order(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "orders"
    __table_args__ = (
        # generate-daily must never create two subscription meals for the same customer/date/session
        Index(
            "uq_orders_subscription_customer_date_session",
            "customer_id", "order_date", "meal_session",
            unique=True,
            postgresql_where=text("order_type = 'SUBSCRIPTION'"),
        ),
        Index("ix_orders_date_driver", "order_date", "assigned_driver_id"),
    )

    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    # Snapshot of customer details at order time
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_address: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    meal_session: Mapped[MealSession] = mapped_column(str_enum(MealSession, "meal_session"), nullable=False)
    diet_type: Mapped[DietType] = mapped_column(str_enum(DietType, "diet_type"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_type: Mapped[OrderType] = mapped_column(str_enum(OrderType, "order_type"), nullable=False)
    spice_level: Mapped[SpiceLevel] = mapped_column(
        str_enum(SpiceLevel, "spice_level"), nullable=False, default=SpiceLevel.NORMAL
    )
    rice_preference: Mapped[Optional[str]] = mapped_column(String(100))
    special_notes: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus, "order_status"), nullable=False, default=OrderStatus.PLANNED, index=True
    )
    status_reason: Mapped[Optional[str]] = mapped_column(String(100))
    assigned_driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_driver_name: Mapped[Optional[str]] = mapped_column(String(100))
    sequence_number: Mapped[Optional[int]] = mapped_column(Integer)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(100))
    proof_photo_url: Mapped[Optional[str]] = mapped_column(Text)

    delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))

    out_for_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


def order_helper(order: Optional[Order]) -> Dict[str, Any]:
    """Serializes an Order row into the API's order dictionary."""
    if not order:
        return {}
    return {
        "id": str(order.id),
        "order_date": order.order_date.isoformat(),
        "customer_id": str(order.customer_id),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address or {},
        "meal_session": ev(order.meal_session),
        "diet_type": ev(order.diet_type),
        "quantity": order.quantity,
        "order_type": ev(order.order_type),
        "spice_level": ev(order.spice_level),
        "rice_preference": order.rice_preference,
        "special_notes": order.special_notes,
        "status": ev(order.status),
        "assigned_driver_id": str(order.assigned_driver_id) if order.assigned_driver_id else None,
        "assigned_driver_name": order.assigned_driver_name,
        "sequence_number": order.sequence_number,
        "delivery_notes": order.delivery_notes,
        "delivery_charge": money(order.delivery_charge),
        "total_price": money(order.total_price),
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
