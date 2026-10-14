import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models._types import str_enum


class LedgerEntryType(str, enum.Enum):
    SUBSCRIPTION_CHARGE = "SUBSCRIPTION_CHARGE"
    ORDER_CHARGE = "ORDER_CHARGE"
    DELIVERY_FEE = "DELIVERY_FEE"
    SKIP_CREDIT = "SKIP_CREDIT"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    PAYMENT = "PAYMENT"


class CustomerLedgerEntry(UUIDPrimaryKey, Base):
    """
    Append-only customer account. Positive amounts increase what the customer owes;
    negative amounts (credits, payments) reduce it. Balance = sum of amounts; below zero is an advance.
    """
    __tablename__ = "customer_ledger_entries"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    entry_type: Mapped[LedgerEntryType] = mapped_column(str_enum(LedgerEntryType, "ledger_entry_type"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"))
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("one_time_orders.id"))
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_tasks.id"))
    payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    # Same key = same posting; protects against double charges, credits and payments
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    OTHER = "OTHER"


class Payment(UUIDPrimaryKey, Timestamps, Base):
    """A manually recorded payment. Gateway payments can later create the same record."""
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_positive"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod, "payment_method"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(120))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    recorded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)


class PaymentAllocation(UUIDPrimaryKey, Base):
    """Admin-chosen allocation of a payment to a subscription or order. Never automatic."""
    __tablename__ = "payment_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_allocations_positive"),
        CheckConstraint("(subscription_id IS NULL) <> (order_id IS NULL)", name="ck_payment_allocations_one_target"),
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"))
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("one_time_orders.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
