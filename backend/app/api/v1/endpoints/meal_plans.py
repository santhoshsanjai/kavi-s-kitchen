from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.schemas.meal_plan import (
    MealPlanCreate,
    MealPlanUpdate,
    MealPlanResponse
)
from app.schemas.customer import DietType
from app.core.database import get_db
from app.models.meal_plan import MealPlan, meal_plan_helper
from app.api.deps import ADMIN_ROLES, parse_uuid, require_roles, get_current_active_user

router = APIRouter()

admin_access = require_roles(ADMIN_ROLES)


async def _get_plan_or_404(db: AsyncSession, plan_id: str) -> MealPlan:
    plan = await db.get(MealPlan, parse_uuid(plan_id, "Meal plan not found"))
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")
    return plan


async def _ensure_unique_name(db: AsyncSession, name: str, exclude_id=None) -> None:
    query = exists().where(MealPlan.name == name)
    if exclude_id is not None:
        query = query.where(MealPlan.id != exclude_id)
    if await db.scalar(select(query)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Meal plan '{name}' already exists.")


@router.get("", response_model=List[MealPlanResponse])
async def get_meal_plans(
    is_active: Optional[bool] = None,
    diet_type: Optional[DietType] = None,
    _: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MealPlan).order_by(MealPlan.price)
    if is_active is not None:
        query = query.where(MealPlan.is_active == is_active)
    if diet_type:
        query = query.where(MealPlan.diet_type == diet_type)
    return [meal_plan_helper(p) for p in (await db.execute(query)).scalars().all()]


@router.post("", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    plan_in: MealPlanCreate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_unique_name(db, plan_in.name)
    plan = MealPlan(**plan_in.model_dump(mode="json"))
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return meal_plan_helper(plan)


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(
    plan_id: str,
    _: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return meal_plan_helper(await _get_plan_or_404(db, plan_id))


@router.put("/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_id: str,
    plan_in: MealPlanUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_plan_or_404(db, plan_id)
    update_data = {k: v for k, v in plan_in.model_dump(mode="json", exclude_unset=True).items() if v is not None}
    if "name" in update_data:
        await _ensure_unique_name(db, update_data["name"], exclude_id=plan.id)
    for field, value in update_data.items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return meal_plan_helper(plan)


@router.delete("/{plan_id}", response_model=dict)
async def delete_meal_plan(
    plan_id: str,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_plan_or_404(db, plan_id)
    await db.delete(plan)
    await db.commit()
    return {"message": "Meal plan deleted successfully", "id": plan_id}
