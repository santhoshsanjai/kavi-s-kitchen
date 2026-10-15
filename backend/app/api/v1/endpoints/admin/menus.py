"""Food items and weekly menus (draft, publish, change notices)."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import parse_uuid
from app.api.serialize import row
from app.api.v1.endpoints.admin._common import Admin, actor
from app.core.database import get_db
from app.core.time import utcnow
from app.domain.meal_windows import MealWindow
from app.models.menu import DietLabel, FoodItem, InboxItem
from app.services import menu_service
from app.services.common import audit
from app.services.errors import Conflict, NotFound

router = APIRouter()


class FoodItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    diet_label: DietLabel
    image_url: Optional[str] = None
    is_available: bool = True


class EntryIn(BaseModel):
    service_date: date
    meal_window: MealWindow
    food_item_id: str


class EntriesIn(BaseModel):
    entries: List[EntryIn]


@router.get("/food-items")
async def list_food_items(_: dict = Admin, db: AsyncSession = Depends(get_db)):
    return [row(f) for f in (await db.execute(select(FoodItem).order_by(FoodItem.name))).scalars().all()]


async def _save_item(db: AsyncSession, item: FoodItem, body: FoodItemIn, user: dict, action: str):
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise Conflict(f"A dish named '{body.name}' already exists")
    audit(db, actor(user), action, "food_item", item.id, data=body.model_dump(mode="json"))
    await db.commit()
    return row(item)


@router.post("/food-items", status_code=201)
async def create_food_item(body: FoodItemIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    item = FoodItem()
    db.add(item)
    return await _save_item(db, item, body, user, "food_item.created")


@router.put("/food-items/{item_id}")
async def update_food_item(item_id: str, body: FoodItemIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    item = await db.get(FoodItem, parse_uuid(item_id, "Dish not found"))
    if item is None:
        raise NotFound("Dish not found")
    return await _save_item(db, item, body, user, "food_item.updated")


async def _menu_out(db: AsyncSession, menu) -> dict:
    draft = await menu_service.draft_snapshot(db, menu)
    return {**row(menu), "draft_entries": draft, "has_unpublished_changes": draft != menu.published_entries}


@router.get("/menus/{week_start}")
async def get_menu(week_start: date, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    menu = await menu_service.get_or_create_menu(db, menu_service.week_start_of(week_start))
    await db.commit()
    return await _menu_out(db, menu)


@router.put("/menus/{week_start}/entries")
async def set_entries(week_start: date, body: EntriesIn, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    menu = await menu_service.get_or_create_menu(db, week_start)
    await menu_service.set_draft_entries(db, menu, [
        menu_service.EntryInput(e.service_date, e.meal_window, parse_uuid(e.food_item_id, "Dish not found"))
        for e in body.entries])
    audit(db, actor(user), "menu.draft_saved", "weekly_menu", menu.id, data={"entries": len(body.entries)})
    await db.commit()
    return await _menu_out(db, menu)


@router.post("/menus/{week_start}/publish")
async def publish_menu(week_start: date, user: dict = Admin, db: AsyncSession = Depends(get_db)):
    menu = await menu_service.get_or_create_menu(db, week_start)
    notified = await menu_service.publish(db, menu, actor(user), utcnow())
    await db.commit()
    return {**(await _menu_out(db, menu)), "notified_customers": notified}


@router.get("/customers/{customer_id}/inbox")
async def customer_inbox(customer_id: str, _: dict = Admin, db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(InboxItem).where(
        InboxItem.customer_id == parse_uuid(customer_id, "Customer not found"))
        .order_by(InboxItem.created_at.desc()).limit(100))).scalars().all()
    return [row(i) for i in items]
