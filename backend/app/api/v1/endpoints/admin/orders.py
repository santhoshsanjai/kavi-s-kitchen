"""One-time order requests: admin creates or reviews them, then confirms price or rejects."""
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import row
from app.api.v1.endpoints.admin._common import Admin, actor, optional_uuid
from app.core.database import get_db
from app.core.time import utcnow
from app.domain.meal_windows import MealWindow
from app.models.customer import Customer
from app.models.one_time_order import OneTimeOrder, OneTimeOrderLine, OneTimeOrderStatus, OrderSource
from app.services import one_time_order_service as orders
from app.services.errors import NotFound, ValidationFailed

router = APIRouter()


class LineIn(BaseModel):
    service_date: date
    meal_window: MealWindow
    quantity: int = Field(default=1, ge=1)
    description: Optional[str] = None


class OrderIn(BaseModel):
    customer_id: str
    lines: List[LineIn]
    notes: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=80)


class ConfirmIn(BaseModel):
    unit_prices: Dict[str, Decimal]  # line id -> confirmed price
    estimated_delivery_fee: Decimal = Field(default=Decimal("0"), ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)


class RejectIn(BaseModel):
    reason: Optional[str] = None


async def _order_out(db: AsyncSession, order: OneTimeOrder) -> dict:
    customer = await db.get(Customer, order.customer_id)
    lines = (await db.execute(select(OneTimeOrderLine).where(OneTimeOrderLine.order_id == order.id)
                              .order_by(OneTimeOrderLine.service_date))).scalars().all()
    subtotal = sum(((l.unit_price or 0) * l.quantity for l in lines), Decimal("0"))
    return row(order, customer_name=customer.name if customer else None,
               customer_phone=customer.phone if customer else None,
               lines=[row(l) for l in lines], subtotal=subtotal,
               total=subtotal - (order.discount or 0) if order.status == OneTimeOrderStatus.CONFIRMED else None)


@router.get("/one-time-orders")
async def list_orders(status: Optional[OneTimeOrderStatus] = None, customer_id: Optional[str] = None,
                      _: dict = Admin, db: AsyncSession = Depends(get_db)):
    q = select(OneTimeOrder).order_by(OneTimeOrder.created_at.desc())
    if status:
        q = q.where(OneTimeOrder.status == status)
    if customer_id:
        q = q.where(OneTimeOrder.customer_id == optional_uuid(customer_id))
    return [await _order_out(db, o) for o in (await db.execute(q.limit(300))).scalars().all()]


@router.post("/one-time-orders", status_code=201)
async def create_order(body: OrderIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    order = await orders.submit_request(
        db, customer_id=parse_uuid(body.customer_id, "Customer not found"),
        lines=[orders.RequestedLine(l.service_date, l.meal_window, l.quantity, l.description) for l in body.lines],
        source=OrderSource.ADMIN, actor_id=actor(user), idempotency_key=body.idempotency_key, notes=body.notes)
    await db.commit()
    return await _order_out(db, order)


@router.get("/one-time-orders/{order_id}")
async def get_order(order_id: str, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    order = await db.get(OneTimeOrder, parse_uuid(order_id, "Order not found"))
    if order is None:
        raise NotFound("Order not found")
    return await _order_out(db, order)


@router.post("/one-time-orders/{order_id}/confirm")
async def confirm_order(order_id: str, body: ConfirmIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    try:
        prices = {parse_uuid(k): v for k, v in body.unit_prices.items()}
    except Exception:
        raise ValidationFailed("Unknown order line")
    order = await orders.confirm(db, order_id=parse_uuid(order_id, "Order not found"), unit_prices=prices,
                                 actor_id=actor(user), now=utcnow(),
                                 estimated_delivery_fee=body.estimated_delivery_fee, discount=body.discount)
    await db.commit()
    return await _order_out(db, order)


@router.post("/one-time-orders/{order_id}/reject")
async def reject_order(order_id: str, body: RejectIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    order = await orders.reject(db, order_id=parse_uuid(order_id, "Order not found"), reason=body.reason,
                                actor_id=actor(user))
    await db.commit()
    return await _order_out(db, order)
