from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models._types import ev, str_enum
from app.schemas.user import UserRole


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "user_role"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Driver profile fields (move to a Driver table with driver codes in Phase 1)
    driving_status: Mapped[str] = mapped_column(String(20), nullable=False, default="AVAILABLE")
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(50))
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(30))
    last_latitude: Mapped[Optional[float]] = mapped_column(Float)
    last_longitude: Mapped[Optional[float]] = mapped_column(Float)
    last_location_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


def user_helper(user: Optional[User]) -> Dict[str, Any]:
    """Serializes a User row into the API's user dictionary."""
    if not user:
        return {}
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": ev(user.role),
        "is_active": user.is_active,
        "driving_status": user.driving_status,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
