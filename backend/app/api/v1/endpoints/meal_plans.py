from fastapi import APIRouter, HTTPException, status, Depends, Query
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone

from app.schemas.meal_plan import (
    MealPlanCreate,
    MealPlanUpdate,
    MealPlanResponse
)
from app.schemas.customer import DietType
from app.schemas.user import UserRole
from app.core import database
from app.models.meal_plan import meal_plan_helper
from app.api.deps import require_roles, get_current_active_user

router = APIRouter()

admin_access = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])


@router.get("", response_model=List[MealPlanResponse])
async def get_meal_plans(
    is_active: Optional[bool] = None,
    diet_type: Optional[DietType] = None,
    _: dict = Depends(get_current_active_user)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if diet_type:
        query["diet_type"] = diet_type

    cursor = database.db.meal_plans.find(query).sort("price", 1)
    items = []
    async for doc in cursor:
        items.append(meal_plan_helper(doc))
    return items


@router.post("", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    plan_in: MealPlanCreate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    doc = plan_in.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)

    result = await database.db.meal_plans.insert_one(doc)
    doc["_id"] = result.inserted_id

    return meal_plan_helper(doc)


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(
    plan_id: str,
    _: dict = Depends(get_current_active_user)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(plan_id)}
    except Exception:
        query = {"id": plan_id}

    plan = await database.db.meal_plans.find_one(query)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    return meal_plan_helper(plan)


@router.put("/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_id: str,
    plan_in: MealPlanUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(plan_id)}
    except Exception:
        query = {"id": plan_id}

    existing = await database.db.meal_plans.find_one(query)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    update_data = {k: v for k, v in plan_in.model_dump(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)

    await database.db.meal_plans.update_one(query, {"$set": update_data})
    updated = await database.db.meal_plans.find_one(query)
    return meal_plan_helper(updated)


@router.delete("/{plan_id}", response_model=dict)
async def delete_meal_plan(
    plan_id: str,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(plan_id)}
    except Exception:
        query = {"id": plan_id}

    result = await database.db.meal_plans.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    return {"message": "Meal plan deleted successfully", "id": plan_id}
