"""Monthly subscriptions: preview, activation, the meal grid, and admin skip/restore."""
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import jsonable, row
from app.api.v1.endpoints.admin._common import Admin, actor, optional_uuid, parse_month
from app.core.database import get_db
from app.core.time import utcnow
from app.domain.meal_windows import MEAL_WINDOW_ORDER, MealWindow
from app.domain.task_states import TaskStatus
from app.models.customer import Customer
from app.models.delivery import DeliveryTask
from app.models.meal_plan import MealPlan
from app.models.subscription import Subscription, SubscriptionMealSlot, SubscriptionStatus
from app.services import subscription_service
from app.services.errors import NotFound

router = APIRouter()


class PreviewIn(BaseModel):
    plan_id: str
    service_month: str


class ActivateIn(PreviewIn):
    customer_id: str


class SlotTarget(BaseModel):
    service_date: date
    meal_window: Optional[MealWindow] = None  # None = whole day


class SkipIn(BaseModel):
    targets: List[SlotTarget]
    reason: Optional[str] = None


def _targets(body: SkipIn):
    return [(t.service_date, t.meal_window) for t in body.targets]


def _preview_out(pv) -> dict:
    return {
        "service_month": pv.service_month.isoformat(),
        "service_dates": jsonable(pv.service_dates),
        "service_days": len(pv.service_dates),
        "included_meals": jsonable(pv.included_meals),
        "total_slots": pv.total_slots,
        "plan_amount": float(pv.plan_amount),
        "per_meal_value": float(pv.per_meal_value_display),
    }


async def _subscription_out(db: AsyncSession, sub: Subscription, with_slots: bool = False) -> dict:
    customer = await db.get(Customer, sub.customer_id)
    plan = await db.get(MealPlan, sub.plan_id)
    out = row(sub, customer_name=customer.name if customer else None, plan_name=plan.name if plan else None)
    out["per_meal_value"] = round(float(sub.per_meal_value), 2)
    if with_slots:
        slots = (await db.execute(select(SubscriptionMealSlot).where(SubscriptionMealSlot.subscription_id == sub.id)
                                  .order_by(SubscriptionMealSlot.service_date))).scalars().all()
        out["slots"] = [row(s) for s in sorted(
            slots, key=lambda s: (s.service_date, MEAL_WINDOW_ORDER.index(s.meal_window)))]
    return out


@router.post("/subscriptions/preview")
async def preview(body: PreviewIn, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    pv, rate = await subscription_service.preview(
        db, plan_id=parse_uuid(body.plan_id, "Plan not found"), service_month=parse_month(body.service_month))
    await db.rollback()  # preview never saves (a first-time rate snapshot is re-created on activation)
    return _preview_out(pv)


@router.post("/subscriptions", status_code=201)
async def activate(body: ActivateIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    sub = await subscription_service.activate(
        db, customer_id=parse_uuid(body.customer_id, "Customer not found"),
        plan_id=parse_uuid(body.plan_id, "Plan not found"), service_month=parse_month(body.service_month),
        actor_id=actor(user), now=utcnow())
    await db.commit()
    return await _subscription_out(db, sub)


@router.get("/subscriptions")
async def list_subscriptions(month: Optional[str] = None, customer_id: Optional[str] = None,
                             status: Optional[SubscriptionStatus] = None, _: dict = Admin,
                             db: AsyncSession = Depends(get_db)):
    q = select(Subscription).order_by(Subscription.service_month.desc(), Subscription.created_at.desc())
    if month:
        q = q.where(Subscription.service_month == parse_month(month))
    if customer_id:
        q = q.where(Subscription.customer_id == optional_uuid(customer_id))
    if status:
        q = q.where(Subscription.status == status)
    return [await _subscription_out(db, s) for s in (await db.execute(q.limit(500))).scalars().all()]


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    sub = await db.get(Subscription, parse_uuid(subscription_id, "Subscription not found"))
    if sub is None:
        raise NotFound("Subscription not found")
    return await _subscription_out(db, sub, with_slots=True)


@router.post("/subscriptions/{subscription_id}/skip-preview")
async def skip_preview(subscription_id: str, body: SkipIn, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    lines, credit = await subscription_service.preview_skip(
        db, subscription_id=parse_uuid(subscription_id, "Subscription not found"), targets=_targets(body), now=utcnow())
    return {
        "meals": [{"service_date": l.service_date.isoformat(), "meal_window": l.meal_window.value,
                   "on_time": l.on_time, "blocked": l.blocked} for l in lines],
        "on_time": sum(l.on_time for l in lines),
        "late": sum(not l.on_time for l in lines),
        "blocked": sum(l.blocked for l in lines),
        "credit": float(credit),
    }


def _skip_out(result) -> dict:
    return {"meals": result.skipped, "credit_eligible": result.credit_eligible, "late": result.late,
            "credit_posted": float(result.credit_posted)}


@router.post("/subscriptions/{subscription_id}/skip")
async def skip(subscription_id: str, body: SkipIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    result = await subscription_service.skip_meals(
        db, subscription_id=parse_uuid(subscription_id, "Subscription not found"), targets=_targets(body),
        reason=body.reason, actor_id=actor(user), now=utcnow())
    await db.commit()
    return _skip_out(result)


@router.post("/subscriptions/{subscription_id}/restore")
async def restore(subscription_id: str, body: SkipIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    result = await subscription_service.restore_meals(
        db, subscription_id=parse_uuid(subscription_id, "Subscription not found"), targets=_targets(body),
        reason=body.reason, actor_id=actor(user))
    await db.commit()
    return _skip_out(result)


@router.get("/meal-grid")
async def meal_grid(month: str, customer_id: Optional[str] = None, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    """Customer x date x meal grid for one month: slot status plus any live delivery task status."""
    first = parse_month(month)
    q = (select(Subscription, Customer.name, MealPlan.name)
         .join(Customer, Customer.id == Subscription.customer_id)
         .join(MealPlan, MealPlan.id == Subscription.plan_id)
         .where(Subscription.service_month == first, Subscription.status != SubscriptionStatus.CANCELLED)
         .order_by(Customer.name))
    if customer_id:
        q = q.where(Subscription.customer_id == optional_uuid(customer_id))
    subs = (await db.execute(q)).all()
    sub_ids = [s.id for s, _, _ in subs]
    slots = (await db.execute(select(SubscriptionMealSlot).where(
        SubscriptionMealSlot.subscription_id.in_(sub_ids)))).scalars().all() if sub_ids else []
    slot_ids = [s.id for s in slots]
    tasks: Dict = {}
    if slot_ids:
        for t in (await db.execute(select(DeliveryTask).where(
                DeliveryTask.slot_id.in_(slot_ids), DeliveryTask.status != TaskStatus.CANCELLED))).scalars().all():
            tasks[t.slot_id] = t.status.value

    by_sub: Dict = {}
    dates = set()
    for s in slots:
        dates.add(s.service_date)
        by_sub.setdefault(s.subscription_id, {}).setdefault(s.service_date.isoformat(), {})[s.meal_window.value] = {
            "slot_id": str(s.id), "status": s.status.value, "credit_eligible": s.skip_credit_eligible,
            "task_status": tasks.get(s.id),
        }
    return {
        "month": first.isoformat(),
        "dates": sorted(d.isoformat() for d in dates),
        "rows": [{
            "subscription_id": str(sub.id), "customer_id": str(sub.customer_id), "customer_name": cname,
            "plan_name": pname, "included_meals": sub.included_meals, "status": sub.status.value,
            "per_meal_value": round(float(sub.per_meal_value), 2),
            "credited_skip_total": float(sub.credited_skip_total), "cells": by_sub.get(sub.id, {}),
        } for sub, cname, pname in subs],
    }
