from typing import Any, Dict, Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models._types import ev, str_enum
from app.schemas.customer import CustomerType


class Customer(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(20))
    customer_type: Mapped[CustomerType] = mapped_column(
        str_enum(CustomerType, "customer_type"), nullable=False, default=CustomerType.INDIVIDUAL
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    # Kept as documents to preserve the current API shape; CustomerAddress gets its own table in Phase 1.
    address: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    meal_preference: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text)


def customer_helper(customer: Optional[Customer]) -> Dict[str, Any]:
    """Serializes a Customer row into the API's customer dictionary."""
    if not customer:
        return {}
    return {
        "id": str(customer.id),
        "name": customer.name,
        "phone": customer.phone,
        "alternate_phone": customer.alternate_phone,
        "whatsapp_number": customer.whatsapp_number,
        "customer_type": ev(customer.customer_type),
        "is_active": customer.is_active,
        "address": customer.address or {},
        "meal_preference": customer.meal_preference or {},
        "notes": customer.notes,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
    }
