"""Business settings (effective-dated), service calendar and plan rate versions."""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import jsonable, row
from app.api.v1.endpoints.admin._common import Admin, actor, parse_month
from app.core.database import get_db
from app.core.time import business_today
from app.domain.meal_windows import MealWindow
from app.domain.service_calendar import month_dates
from app.models.meal_plan import MealPlan
from app.models.settings import ServiceDateException, SettingsVersion
from app.models.subscription import PlanRateVersion
from app.schemas.settings import BusinessSettings
from app.services import settings_service, subscription_service
from app.services.errors import NotFound

router = APIRouter()


class SettingsVersionIn(BaseModel):
    effective_from: date
    settings: BusinessSettings
    reason: str


class DateExceptionIn(BaseModel):
    service_date: date
    is_open: bool = False
    reason: str


class RateVersionIn(BaseModel):
    effective_from: date
    monthly_amount: Decimal = Field(ge=0)
    included_meals: List[MealWindow]
    reason: str


@router.get("/settings")
async def current_settings(on: date | None = None, _: dict = Admin, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    on = on or business_today()
    version, data = await settings_service.get_settings(db, on)
    versions = (await db.execute(select(SettingsVersion).order_by(SettingsVersion.effective_from.desc()))).scalars().all()
    return {
        "on": on.isoformat(),
        "version": row(version, exclude=["data"]),
        "settings": data.model_dump(mode="json"),
        "uses_defaults": version is None,
        "versions": [row(v, exclude=["data"]) for v in versions],
    }


@router.post("/settings/versions", status_code=201)
async def create_settings_version(body: SettingsVersionIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    version = await settings_service.save_settings_version(
        db, effective_from=body.effective_from, settings=body.settings, actor_id=actor(user), reason=body.reason)
    await db.commit()
    return row(version)


@router.get("/calendar")
async def calendar(month: str, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    first = parse_month(month)
    days = month_dates(first)
    _, settings = await settings_service.get_settings(db, first)
    service_dates = await settings_service.service_dates_for_month(db, first, settings)
    exceptions = (await db.execute(select(ServiceDateException).where(
        ServiceDateException.service_date.between(days[0], days[-1])).order_by(ServiceDateException.service_date)
    )).scalars().all()
    return {
        "month": first.isoformat(),
        "service_weekdays": settings.calendar.service_weekdays,
        "allow_open_overrides": settings.calendar.allow_open_overrides,
        "service_dates": jsonable(service_dates),
        "exceptions": [row(e) for e in exceptions],
    }


@router.put("/calendar/exceptions")
async def set_date_exception(body: DateExceptionIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    exc = await settings_service.set_service_date_exception(
        db, service_date=body.service_date, is_open=body.is_open, reason=body.reason, actor_id=actor(user))
    await db.commit()
    return row(exc)


@router.get("/plans/{plan_id}/rates")
async def plan_rates(plan_id: str, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    pid = parse_uuid(plan_id, "Plan not found")
    plan = await db.get(MealPlan, pid)
    if plan is None:
        raise NotFound("Plan not found")
    rates = (await db.execute(select(PlanRateVersion).where(PlanRateVersion.plan_id == pid)
                              .order_by(PlanRateVersion.effective_from.desc()))).scalars().all()
    return {"plan_id": str(pid), "plan_name": plan.name, "current_price": float(plan.price),
            "rates": [row(r) for r in rates]}


@router.post("/plans/{plan_id}/rates", status_code=201)
async def add_plan_rate(plan_id: str, body: RateVersionIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    rate = await subscription_service.add_rate_version(
        db, plan_id=parse_uuid(plan_id, "Plan not found"), effective_from=body.effective_from,
        monthly_amount=body.monthly_amount, included_meals=body.included_meals, reason=body.reason,
        actor_id=actor(user))
    await db.commit()
    return row(rate)
