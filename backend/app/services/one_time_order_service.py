import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.meal_windows import MealWindow
from app.domain.money import round_money, to_decimal
from app.models.customer import Customer
from app.models.ledger import LedgerEntryType
from app.models.one_time_order import OneTimeOrder, OneTimeOrderLine, OneTimeOrderStatus, OrderSource
from app.services.common import audit, lock, post_ledger, require_reason
from app.services.errors import Conflict, NotFound, ValidationFailed


@dataclass
class RequestedLine:
    service_date: date
    meal_window: MealWindow
    quantity: int = 1
    description: Optional[str] = None


async def submit_request(db: AsyncSession, *, customer_id: uuid.UUID, lines: List[RequestedLine],
                         source: OrderSource, actor_id: Optional[uuid.UUID], idempotency_key: Optional[str] = None,
                         notes: Optional[str] = None, enquiry_id: Optional[uuid.UUID] = None) -> OneTimeOrder:
    """Creates a request that stays REQUEST_PENDING until an admin confirms price, availability and delivery."""
    if idempotency_key:
        existing = (await db.execute(
            select(OneTimeOrder).where(OneTimeOrder.idempotency_key == idempotency_key)
        )).scalars().first()
        if existing is not None:
            if existing.customer_id != customer_id:
                raise Conflict("Idempotency key already used")
            return existing
    customer = await db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise NotFound("Customer not found or inactive")
    if not lines or any(line.quantity < 1 for line in lines):
        raise ValidationFailed("A request needs at least one meal with a quantity of 1 or more")

    order = OneTimeOrder(customer_id=customer_id, enquiry_id=enquiry_id, source=source,
                         status=OneTimeOrderStatus.REQUEST_PENDING, delivery_address=customer.address or {},
                         request_notes=notes, idempotency_key=idempotency_key)
    db.add(order)
    await db.flush()
    db.add_all([OneTimeOrderLine(order_id=order.id, service_date=l.service_date, meal_window=l.meal_window,
                                 quantity=l.quantity, description=l.description) for l in lines])
    audit(db, actor_id, "order.requested", "one_time_order", order.id, data={"source": source.value})
    return order


async def confirm(db: AsyncSession, *, order_id: uuid.UUID, unit_prices: Dict[uuid.UUID, Decimal],
                  actor_id: uuid.UUID, now: datetime, estimated_delivery_fee: Decimal = Decimal("0"),
                  discount: Decimal = Decimal("0")) -> OneTimeOrder:
    """Admin confirms availability, price and delivery. Confirming twice changes nothing."""
    order = await lock(db, OneTimeOrder, order_id, "Order")
    if order.status == OneTimeOrderStatus.CONFIRMED:
        return order
    if order.status != OneTimeOrderStatus.REQUEST_PENDING:
        raise Conflict(f"Cannot confirm an order that is {order.status.value}")

    lines = (await db.execute(select(OneTimeOrderLine).where(OneTimeOrderLine.order_id == order.id))).scalars().all()
    missing = [l for l in lines if l.id not in unit_prices]
    if missing:
        raise ValidationFailed("Every line needs a confirmed price")
    subtotal = Decimal("0")
    for line in lines:
        price = to_decimal(unit_prices[line.id])
        if price < 0:
            raise ValidationFailed("Prices cannot be negative")
        line.unit_price = round_money(price)
        subtotal += line.unit_price * line.quantity
    discount = round_money(discount)
    if discount < 0 or discount > subtotal:
        raise ValidationFailed("Discount must be between 0 and the order subtotal")

    order.status = OneTimeOrderStatus.CONFIRMED
    order.confirmed_at = now
    order.confirmed_by_id = actor_id
    order.discount = discount
    order.estimated_delivery_fee = round_money(estimated_delivery_fee)
    await post_ledger(db, customer_id=order.customer_id, entry_type=LedgerEntryType.ORDER_CHARGE,
                      amount=round_money(subtotal - discount), order_id=order.id, created_by_id=actor_id,
                      description="One-time order", idempotency_key=f"order:{order.id}:charge")
    audit(db, actor_id, "order.confirmed", "one_time_order", order.id,
          data={"subtotal": str(subtotal), "discount": str(discount)})
    return order


async def reject(db: AsyncSession, *, order_id: uuid.UUID, reason: str, actor_id: uuid.UUID) -> OneTimeOrder:
    reason = require_reason(reason, "Rejecting a request")
    order = await lock(db, OneTimeOrder, order_id, "Order")
    if order.status != OneTimeOrderStatus.REQUEST_PENDING:
        raise Conflict(f"Cannot reject an order that is {order.status.value}")
    order.status = OneTimeOrderStatus.REJECTED
    order.rejection_reason = reason
    audit(db, actor_id, "order.rejected", "one_time_order", order.id, reason)
    return order
