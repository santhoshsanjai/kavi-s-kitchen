import enum
import uuid
from datetime import date, datetime
from typing import Any, List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.meal_windows import MealWindow
from app.models._types import str_enum


class DietLabel(str, enum.Enum):
    VEG = "VEG"
    NON_VEG = "NON_VEG"
    EGG = "EGG"


class FoodItem(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "food_items"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    diet_label: Mapped[DietLabel] = mapped_column(str_enum(DietLabel, "diet_label"), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    # Admin-controlled; no stock-based automatic unavailability in the first release
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MenuStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class WeeklyMenu(UUIDPrimaryKey, Timestamps, Base):
    """
    Admins edit draft entries; publishing copies them into published_entries, which is all the
    customer app ever sees. Publishing again after a change notifies affected customers.
    """
    __tablename__ = "weekly_menus"

    week_start: Mapped[date] = mapped_column(Date, nullable=False, unique=True)  # a Monday
    status: Mapped[MenuStatus] = mapped_column(str_enum(MenuStatus, "menu_status"), nullable=False, default=MenuStatus.DRAFT)
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_entries: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class MenuEntry(UUIDPrimaryKey, Base):
    """Draft menu content: a dish on a date and meal window."""
    __tablename__ = "menu_entries"
    __table_args__ = (UniqueConstraint("menu_id", "service_date", "meal_window", "food_item_id"),)

    menu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("weekly_menus.id", ondelete="CASCADE"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_window: Mapped[MealWindow] = mapped_column(str_enum(MealWindow, "meal_window"), nullable=False)
    food_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("food_items.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class InboxItem(UUIDPrimaryKey, Base):
    """In-app notice for a customer or a staff user. Notices are not the source of truth; database state is."""
    __tablename__ = "inbox_items"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
