import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.meal_windows import MealWindow
from app.domain.task_states import TaskStatus
from app.models._types import str_enum


class TaskType(str, enum.Enum):
    SUBSCRIPTION = "SUBSCRIPTION"
    ONE_TIME = "ONE_TIME"


class TripStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    STARTED = "STARTED"
    ENDED = "ENDED"


class DistanceStatus(str, enum.Enum):
    NOT_CALCULATED = "NOT_CALCULATED"
    CALCULATED = "CALCULATED"
    # Maps could not route the trip; an admin must enter an audited manual distance
    NEEDS_MANUAL_ENTRY = "NEEDS_MANUAL_ENTRY"


class DeliveryTrip(UUIDPrimaryKey, Timestamps, Base):
    """One driver's breakfast, lunch or dinner run on a date."""
    __tablename__ = "delivery_trips"
    __table_args__ = (UniqueConstraint("driver_id", "service_date", "meal_window"),)

    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_window: Mapped[MealWindow] = mapped_column(str_enum(MealWindow, "meal_window"), nullable=False)
    status: Mapped[TripStatus] = mapped_column(str_enum(TripStatus, "trip_status"), nullable=False, default=TripStatus.PLANNED)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[Optional[str]] = mapped_column(Text)
    distance_status: Mapped[DistanceStatus] = mapped_column(
        str_enum(DistanceStatus, "distance_status"), nullable=False, default=DistanceStatus.NOT_CALCULATED
    )
    include_return_leg: Mapped[Optional[bool]] = mapped_column(Boolean)  # snapshot at trip end
    payable_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))


class DeliveryTask(UUIDPrimaryKey, Timestamps, Base):
    """One delivery to one customer for one meal: from a subscription slot or a confirmed order line."""
    __tablename__ = "delivery_tasks"
    __table_args__ = (
        CheckConstraint("(slot_id IS NULL) <> (order_line_id IS NULL)", name="ck_delivery_tasks_one_source"),
        Index("ix_delivery_tasks_date_window", "service_date", "meal_window"),
        Index("ix_delivery_tasks_driver_date", "assigned_driver_id", "service_date"),
        # One live task per subscription slot / order line. A cancelled task keeps its history and a
        # restored slot gets a new task.
        Index("uq_delivery_tasks_live_slot", "slot_id", unique=True,
              postgresql_where=text("slot_id IS NOT NULL AND status <> 'CANCELLED'")),
        Index("uq_delivery_tasks_live_order_line", "order_line_id", unique=True,
              postgresql_where=text("order_line_id IS NOT NULL AND status <> 'CANCELLED'")),
    )

    task_type: Mapped[TaskType] = mapped_column(str_enum(TaskType, "task_type"), nullable=False)
    slot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_meal_slots.id"))
    order_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("one_time_order_lines.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_window: Mapped[MealWindow] = mapped_column(str_enum(MealWindow, "meal_window"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    items: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
    delivery_address: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[TaskStatus] = mapped_column(str_enum(TaskStatus, "task_status"), nullable=False, default=TaskStatus.PENDING, index=True)
    assigned_driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    trip_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_trips.id"))
    stop_sequence: Mapped[Optional[int]] = mapped_column(Integer)

    delivery_note: Mapped[Optional[str]] = mapped_column(Text)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    delivered_items: Mapped[Optional[List[Any]]] = mapped_column(JSONB)
    missing_items: Mapped[Optional[List[Any]]] = mapped_column(JSONB)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    customer_delivery_charge: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))


class AssignmentStatus(str, enum.Enum):
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class DriverAssignment(UUIDPrimaryKey, Base):
    """History of each offer of a task to a driver. At most one open offer/acceptance per task."""
    __tablename__ = "driver_assignments"
    __table_args__ = (
        Index("uq_driver_assignments_open_per_task", "task_id", unique=True,
              postgresql_where=text("status IN ('OFFERED', 'ACCEPTED')")),
        Index("ix_driver_assignments_expiry", "status", "expires_at"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_tasks.id"), nullable=False)
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(str_enum(AssignmentStatus, "assignment_status"), nullable=False)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decline_reason: Mapped[Optional[str]] = mapped_column(Text)
    assigned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class DeliveryEvent(UUIDPrimaryKey, Base):
    """Every task status change with its actor and time."""
    __tablename__ = "delivery_events"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_tasks.id"), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    from_status: Mapped[Optional[str]] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DistanceSource(str, enum.Enum):
    GOOGLE_MAPS = "GOOGLE_MAPS"
    MANUAL = "MANUAL"


class RouteLeg(UUIDPrimaryKey, Timestamps, Base):
    """Distance of one leg of a trip: kitchen->stop 1, stop n->stop n+1, or last stop->kitchen (return)."""
    __tablename__ = "route_legs"
    __table_args__ = (UniqueConstraint("trip_id", "sequence"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_trips.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    to_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_tasks.id"))
    is_return: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    source: Mapped[DistanceSource] = mapped_column(str_enum(DistanceSource, "distance_source"), nullable=False)
    # Raw provider data for traceability; Maps distance is a route estimate, not GPS-measured
    provider_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    entered_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    manual_reason: Mapped[Optional[str]] = mapped_column(Text)
