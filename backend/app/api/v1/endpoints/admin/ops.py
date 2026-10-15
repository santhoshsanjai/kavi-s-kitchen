"""Dashboard, alerts, audit trail and driver accounts."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import row
from app.api.v1.endpoints.admin._common import Admin, actor
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.time import business_today, utcnow
from app.domain.service_calendar import month_start
from app.models.audit import AdminAlert, AuditLog
from app.models.delivery import DeliveryTask, DeliveryTrip, DistanceStatus
from app.models.ledger import CustomerLedgerEntry
from app.models.one_time_order import OneTimeOrder, OneTimeOrderStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, user_helper
from app.schemas.user import UserRole
from app.services.common import audit
from app.services.errors import Conflict, NotFound

router = APIRouter()


class DriverIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    vehicle_type: Optional[str] = Field(default=None, max_length=50)
    vehicle_number: Optional[str] = Field(default=None, max_length=30)


@router.get("/dashboard")
async def dashboard(service_date: Optional[date] = None, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    day = service_date or business_today()
    by_status = dict((await db.execute(select(DeliveryTask.status, func.count()).where(
        DeliveryTask.service_date == day).group_by(DeliveryTask.status))).all())
    by_window = dict((await db.execute(select(DeliveryTask.meal_window, func.count()).where(
        DeliveryTask.service_date == day).group_by(DeliveryTask.meal_window))).all())
    balances = (await db.execute(select(CustomerLedgerEntry.customer_id, func.sum(CustomerLedgerEntry.amount))
                                 .group_by(CustomerLedgerEntry.customer_id))).all()
    return {
        "service_date": day.isoformat(),
        "active_subscriptions": await db.scalar(select(func.count()).select_from(Subscription).where(
            Subscription.service_month == month_start(day), Subscription.status == SubscriptionStatus.ACTIVE)),
        "tasks_by_status": {k.value: v for k, v in by_status.items()},
        "tasks_by_meal": {k.value: v for k, v in by_window.items()},
        "pending_requests": await db.scalar(select(func.count()).select_from(OneTimeOrder).where(
            OneTimeOrder.status == OneTimeOrderStatus.REQUEST_PENDING)),
        "open_alerts": await db.scalar(select(func.count()).select_from(AdminAlert).where(AdminAlert.resolved_at.is_(None))),
        "trips_needing_distance": await db.scalar(select(func.count()).select_from(DeliveryTrip).where(
            DeliveryTrip.distance_status == DistanceStatus.NEEDS_MANUAL_ENTRY)),
        "outstanding_total": float(sum((b for _, b in balances if b > 0), 0)),
        "advance_total": float(-sum((b for _, b in balances if b < 0), 0)),
    }


@router.get("/alerts")
async def alerts(include_resolved: bool = False, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    q = select(AdminAlert).order_by(AdminAlert.created_at.desc())
    if not include_resolved:
        q = q.where(AdminAlert.resolved_at.is_(None))
    return [row(a) for a in (await db.execute(q.limit(200))).scalars().all()]


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    alert = await db.get(AdminAlert, parse_uuid(alert_id, "Alert not found"))
    if alert is None:
        raise NotFound("Alert not found")
    if alert.resolved_at is None:
        alert.resolved_at = utcnow()
        alert.resolved_by_id = actor(user)
        await db.commit()
    return row(alert)


@router.get("/audit")
async def audit_log(entity_type: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 100,
                    _: dict = Admin, db: AsyncSession = Depends(get_db)):
    q = select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.actor_id).order_by(AuditLog.at.desc())
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    return [row(a, actor_name=name) for a, name in (await db.execute(q.limit(min(max(limit, 1), 500)))).all()]


@router.post("/drivers", status_code=201)
async def create_driver(body: DriverIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    """Creates a driver login. Driver codes are issued in sequence (D001, D002, ...)."""
    codes = (await db.execute(select(User.driver_code).where(User.driver_code.is_not(None)))).scalars().all()
    next_no = max([int(c[1:]) for c in codes if c[1:].isdigit()] + [0]) + 1
    driver = User(full_name=body.full_name, username=body.username, phone=body.phone, email=body.email,
                  hashed_password=get_password_hash(body.password), role=UserRole.DRIVER, is_active=True,
                  driver_code=f"D{next_no:03d}", driving_status="OFFLINE",
                  vehicle_type=body.vehicle_type, vehicle_number=body.vehicle_number)
    db.add(driver)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise Conflict("That username, phone or email is already in use")
    audit(db, actor(user), "driver.created", "user", driver.id, data={"driver_code": driver.driver_code})
    await db.commit()
    return user_helper(driver)
