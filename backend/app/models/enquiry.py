import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models._types import ev, str_enum
from app.schemas.customer import DietType
from app.schemas.enquiry import EnquiryStatus


class Enquiry(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "enquiries"

    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    enquiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    requested_meal: Mapped[Optional[str]] = mapped_column(String(100))
    requested_date: Mapped[Optional[str]] = mapped_column(String(20))
    number_of_persons: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    diet_type: Mapped[DietType] = mapped_column(str_enum(DietType, "diet_type"), nullable=False, default=DietType.VEG)
    subscription_type: Mapped[str] = mapped_column(String(30), nullable=False, default="SUBSCRIPTION")
    delivery_location: Mapped[str] = mapped_column(Text, nullable=False)
    quoted_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_date: Mapped[Optional[str]] = mapped_column(String(20))
    assigned_admin: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[EnquiryStatus] = mapped_column(
        str_enum(EnquiryStatus, "enquiry_status"), nullable=False, default=EnquiryStatus.NEW, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL")
    )


def enquiry_helper(enquiry: Optional[Enquiry]) -> Dict[str, Any]:
    """Serializes an Enquiry row into the API's enquiry dictionary."""
    if not enquiry:
        return {}
    return {
        "id": str(enquiry.id),
        "customer_name": enquiry.customer_name,
        "phone": enquiry.phone,
        "enquiry_date": enquiry.enquiry_date,
        "requested_meal": enquiry.requested_meal,
        "requested_date": enquiry.requested_date,
        "number_of_persons": enquiry.number_of_persons,
        "diet_type": ev(enquiry.diet_type),
        "subscription_type": enquiry.subscription_type,
        "delivery_location": enquiry.delivery_location,
        "quoted_price": float(enquiry.quoted_price) if enquiry.quoted_price is not None else None,
        "notes": enquiry.notes,
        "follow_up_date": enquiry.follow_up_date,
        "assigned_admin": enquiry.assigned_admin,
        "status": ev(enquiry.status),
        "customer_id": str(enquiry.customer_id) if enquiry.customer_id else None,
        "created_at": enquiry.created_at,
        "updated_at": enquiry.updated_at,
    }
