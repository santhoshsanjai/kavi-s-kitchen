"""Customer ledger, payments and manual adjustments; driver daily earnings."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import row
from app.api.v1.endpoints.admin._common import Admin, actor, optional_uuid
from app.core.database import get_db
from app.core.time import business_today, utcnow
from app.models.customer import Customer
from app.models.ledger import CustomerLedgerEntry, Payment, PaymentAllocation, PaymentMethod
from app.models.payout import DriverDaySummary
from app.models.user import User
from app.schemas.user import UserRole
from app.services import earnings_service, payment_service
from app.services.errors import NotFound

router = APIRouter()


class AllocationIn(BaseModel):
    amount: Decimal = Field(gt=0)
    subscription_id: Optional[str] = None
    order_id: Optional[str] = None


class PaymentIn(BaseModel):
    customer_id: str
    method: PaymentMethod
    amount: Decimal = Field(gt=0)
    received_at: Optional[datetime] = None
    reference: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = None
    allocations: List[AllocationIn] = []
    idempotency_key: str = Field(min_length=8, max_length=120)


class AdjustmentIn(BaseModel):
    amount: Decimal  # negative = credit to customer, positive = charge
    reason: Optional[str] = None


class DayIn(BaseModel):
    driver_id: str
    service_date: date


class EarningAdjustmentIn(DayIn):
    amount: Decimal
    reason: Optional[str] = None


@router.get("/ledger/balances")
async def balances(_: dict = Admin, db: AsyncSession = Depends(get_db)):
    """Every customer with ledger activity and their balance (positive = owes, negative = advance)."""
    rows = (await db.execute(
        select(Customer.id, Customer.name, Customer.phone, func.coalesce(func.sum(CustomerLedgerEntry.amount), 0))
        .join(CustomerLedgerEntry, CustomerLedgerEntry.customer_id == Customer.id)
        .group_by(Customer.id).order_by(Customer.name))).all()
    return [{"customer_id": str(cid), "customer_name": name, "phone": phone, "balance": float(bal)}
            for cid, name, phone, bal in rows]


@router.get("/customers/{customer_id}/ledger")
async def customer_ledger(customer_id: str, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    cid = parse_uuid(customer_id, "Customer not found")
    customer = await db.get(Customer, cid)
    if customer is None:
        raise NotFound("Customer not found")
    entries = (await db.execute(select(CustomerLedgerEntry).where(CustomerLedgerEntry.customer_id == cid)
                                .order_by(CustomerLedgerEntry.created_at))).scalars().all()
    running = Decimal("0")
    out = []
    for e in entries:
        running += e.amount
        out.append(row(e, running_balance=running))
    return {"customer_id": str(cid), "customer_name": customer.name,
            "balance": float(await payment_service.customer_balance(db, cid)), "entries": out}


@router.get("/payments")
async def list_payments(customer_id: Optional[str] = None, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    q = select(Payment, Customer.name).join(Customer, Customer.id == Payment.customer_id).order_by(Payment.received_at.desc())
    if customer_id:
        q = q.where(Payment.customer_id == optional_uuid(customer_id))
    out = []
    for p, name in (await db.execute(q.limit(300))).all():
        allocs = (await db.execute(select(PaymentAllocation).where(PaymentAllocation.payment_id == p.id))).scalars().all()
        out.append(row(p, customer_name=name, allocations=[row(a) for a in allocs]))
    return out


@router.post("/payments", status_code=201)
async def record_payment(body: PaymentIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    payment = await payment_service.record_payment(
        db, customer_id=parse_uuid(body.customer_id, "Customer not found"), method=body.method, amount=body.amount,
        received_at=body.received_at or utcnow(), idempotency_key=body.idempotency_key, actor_id=actor(user),
        reference=body.reference, notes=body.notes,
        allocations=[payment_service.Allocation(a.amount, optional_uuid(a.subscription_id), optional_uuid(a.order_id))
                     for a in body.allocations])
    await db.commit()
    return row(payment, balance=await payment_service.customer_balance(db, payment.customer_id))


@router.post("/customers/{customer_id}/adjustments", status_code=201)
async def adjust(customer_id: str, body: AdjustmentIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    cid = parse_uuid(customer_id, "Customer not found")
    await payment_service.manual_adjustment(db, customer_id=cid, amount=body.amount, reason=body.reason,
                                            actor_id=actor(user))
    await db.commit()
    return {"customer_id": str(cid), "balance": float(await payment_service.customer_balance(db, cid))}


async def _summary_out(db: AsyncSession, summary: DriverDaySummary) -> dict:
    driver = await db.get(User, summary.driver_id)
    lines = await earnings_service.lines_for_day(db, summary.id)
    return row(summary, driver_name=driver.full_name if driver else None,
               driver_code=driver.driver_code if driver else None, lines=[row(l) for l in lines])


@router.get("/earnings")
async def earnings(service_date: Optional[date] = None, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    """Saved daily summaries for a date, plus active drivers without one yet."""
    day = service_date or business_today()
    summaries = (await db.execute(select(DriverDaySummary).where(DriverDaySummary.service_date == day))).scalars().all()
    have = {s.driver_id for s in summaries}
    drivers = (await db.execute(select(User).where(User.role == UserRole.DRIVER, User.is_active.is_(True))
                                .order_by(User.full_name))).scalars().all()
    return {"service_date": day.isoformat(),
            "summaries": [await _summary_out(db, s) for s in summaries],
            "not_calculated": [{"driver_id": str(d.id), "driver_name": d.full_name, "driver_code": d.driver_code}
                               for d in drivers if d.id not in have]}


@router.post("/earnings/calculate")
async def calculate(body: DayIn, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    summary = await earnings_service.calculate_day(
        db, driver_id=parse_uuid(body.driver_id, "Driver not found"), service_date=body.service_date)
    await db.commit()
    return await _summary_out(db, summary)


@router.post("/earnings/finalize")
async def finalize(body: DayIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    summary = await earnings_service.finalize_day(
        db, driver_id=parse_uuid(body.driver_id, "Driver not found"), service_date=body.service_date,
        actor_id=actor(user), now=utcnow())
    await db.commit()
    return await _summary_out(db, summary)


@router.post("/earnings/adjustments", status_code=201)
async def earning_adjustment(body: EarningAdjustmentIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    driver_id = parse_uuid(body.driver_id, "Driver not found")
    await earnings_service.add_adjustment(db, driver_id=driver_id, service_date=body.service_date,
                                          amount=body.amount, reason=body.reason, actor_id=actor(user))
    await db.commit()
    summary = (await db.execute(select(DriverDaySummary).where(
        DriverDaySummary.driver_id == driver_id, DriverDaySummary.service_date == body.service_date))).scalars().one()
    return await _summary_out(db, summary)
