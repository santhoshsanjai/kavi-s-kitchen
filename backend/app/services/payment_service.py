import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.money import round_money
from app.models.customer import Customer
from app.models.ledger import CustomerLedgerEntry, LedgerEntryType, Payment, PaymentAllocation, PaymentMethod
from app.models.one_time_order import OneTimeOrder
from app.models.subscription import Subscription
from app.services.common import audit, post_ledger, require_reason
from app.services.errors import Conflict, NotFound, ValidationFailed


@dataclass
class Allocation:
    amount: Decimal
    subscription_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None


async def customer_balance(db: AsyncSession, customer_id: uuid.UUID) -> Decimal:
    """Positive = outstanding; negative = advance/credit available."""
    total = await db.scalar(select(func.coalesce(func.sum(CustomerLedgerEntry.amount), 0))
                            .where(CustomerLedgerEntry.customer_id == customer_id))
    return round_money(total)


async def record_payment(db: AsyncSession, *, customer_id: uuid.UUID, method: PaymentMethod, amount: Decimal,
                         received_at: datetime, idempotency_key: str, actor_id: uuid.UUID,
                         reference: Optional[str] = None, notes: Optional[str] = None,
                         allocations: Optional[List[Allocation]] = None) -> Payment:
    """
    Records cash/UPI/bank/other payments (advance, partial or full). Allocation to subscriptions or orders
    is explicit and optional; money is never applied to invoices automatically.
    """
    existing = (await db.execute(select(Payment).where(Payment.idempotency_key == idempotency_key))).scalars().first()
    if existing is not None:
        if existing.customer_id != customer_id or existing.amount != round_money(amount):
            raise Conflict("Idempotency key already used for a different payment")
        return existing
    if await db.get(Customer, customer_id) is None:
        raise NotFound("Customer not found")
    amount = round_money(amount)
    if amount <= 0:
        raise ValidationFailed("Payment amount must be positive")
    allocations = allocations or []
    if sum((round_money(a.amount) for a in allocations), Decimal("0")) > amount:
        raise ValidationFailed("Allocations cannot exceed the payment amount")
    for a in allocations:
        if (a.subscription_id is None) == (a.order_id is None) or round_money(a.amount) <= 0:
            raise ValidationFailed("Each allocation needs one subscription or order and a positive amount")
        target = await db.get(Subscription, a.subscription_id) if a.subscription_id else await db.get(OneTimeOrder, a.order_id)
        if target is None or target.customer_id != customer_id:
            raise ValidationFailed("Allocations must belong to this customer")

    payment = Payment(customer_id=customer_id, method=method, amount=amount, received_at=received_at,
                      reference=reference, notes=notes, recorded_by_id=actor_id, idempotency_key=idempotency_key)
    db.add(payment)
    await db.flush()
    db.add_all([PaymentAllocation(payment_id=payment.id, subscription_id=a.subscription_id, order_id=a.order_id,
                                  amount=round_money(a.amount)) for a in allocations])
    await post_ledger(db, customer_id=customer_id, entry_type=LedgerEntryType.PAYMENT, amount=-amount,
                      payment_id=payment.id, created_by_id=actor_id,
                      description=f"Payment received ({method.value})", idempotency_key=f"payment:{payment.id}")
    audit(db, actor_id, "payment.recorded", "payment", payment.id,
          data={"amount": str(amount), "method": method.value, "reference": reference})
    return payment


async def manual_adjustment(db: AsyncSession, *, customer_id: uuid.UUID, amount: Decimal, reason: str,
                            actor_id: uuid.UUID) -> None:
    """Itemized manual credit (negative) or charge (positive), e.g. goodwill credit for a late skip."""
    reason = require_reason(reason, "A manual adjustment")
    amount = round_money(amount)
    if amount == 0:
        raise ValidationFailed("Adjustment amount cannot be zero")
    if await db.get(Customer, customer_id) is None:
        raise NotFound("Customer not found")
    await post_ledger(db, customer_id=customer_id, entry_type=LedgerEntryType.MANUAL_ADJUSTMENT, amount=amount,
                      reason=reason, created_by_id=actor_id, description="Manual adjustment",
                      idempotency_key=f"adjustment:{uuid.uuid4()}")
    audit(db, actor_id, "ledger.manual_adjustment", "customer", customer_id, reason, {"amount": str(amount)})
