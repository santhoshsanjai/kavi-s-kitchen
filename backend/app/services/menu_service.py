import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.meal_windows import MEAL_WINDOW_ORDER, MealWindow
from app.models.menu import FoodItem, InboxItem, MenuEntry, MenuStatus, WeeklyMenu
from app.models.subscription import SlotStatus, Subscription, SubscriptionMealSlot, SubscriptionStatus
from app.services.common import audit
from app.services.errors import ValidationFailed


def week_start_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


@dataclass
class EntryInput:
    service_date: date
    meal_window: MealWindow
    food_item_id: uuid.UUID


async def get_or_create_menu(db: AsyncSession, week_start: date) -> WeeklyMenu:
    if week_start.weekday() != 0:
        raise ValidationFailed("A weekly menu starts on a Monday")
    menu = (await db.execute(select(WeeklyMenu).where(WeeklyMenu.week_start == week_start))).scalars().first()
    if menu is None:
        menu = WeeklyMenu(week_start=week_start, status=MenuStatus.DRAFT, published_version=0, published_entries=[])
        db.add(menu)
        await db.flush()
    return menu


async def set_draft_entries(db: AsyncSession, menu: WeeklyMenu, entries: List[EntryInput]) -> None:
    week = {menu.week_start + timedelta(days=i) for i in range(7)}
    item_ids = {e.food_item_id for e in entries}
    found = set((await db.execute(select(FoodItem.id).where(FoodItem.id.in_(item_ids)))).scalars().all()) if item_ids else set()
    if found != item_ids:
        raise ValidationFailed("Unknown food item")
    if any(e.service_date not in week for e in entries):
        raise ValidationFailed("Every dish must be on a date inside this menu's week")
    await db.execute(delete(MenuEntry).where(MenuEntry.menu_id == menu.id))
    for order, e in enumerate(entries):
        db.add(MenuEntry(menu_id=menu.id, service_date=e.service_date, meal_window=e.meal_window,
                         food_item_id=e.food_item_id, sort_order=order))
    await db.flush()


async def draft_snapshot(db: AsyncSession, menu: WeeklyMenu) -> list:
    rows = (await db.execute(
        select(MenuEntry, FoodItem).join(FoodItem, FoodItem.id == MenuEntry.food_item_id)
        .where(MenuEntry.menu_id == menu.id).order_by(MenuEntry.service_date, MenuEntry.sort_order)
    )).all()
    order = {w: i for i, w in enumerate(MEAL_WINDOW_ORDER)}
    rows = sorted(rows, key=lambda r: (r[0].service_date, order[r[0].meal_window], r[0].sort_order))
    return [{
        "service_date": e.service_date.isoformat(), "meal_window": e.meal_window.value,
        "food_item_id": str(f.id), "name": f.name, "description": f.description,
        "diet_label": f.diet_label.value, "image_url": f.image_url, "is_available": f.is_available,
    } for e, f in rows]


async def publish(db: AsyncSession, menu: WeeklyMenu, actor_id: uuid.UUID, now: datetime) -> int:
    """Publishes the draft. Returns how many customers got an in-app notice about a changed menu."""
    snapshot = await draft_snapshot(db, menu)
    if not snapshot:
        raise ValidationFailed("Add dishes before publishing")
    changed = menu.published_version > 0 and snapshot != menu.published_entries
    if menu.published_version > 0 and not changed:
        return 0
    menu.published_entries = snapshot
    menu.published_version += 1
    menu.status = MenuStatus.PUBLISHED
    menu.published_at = now
    menu.published_by_id = actor_id

    notified = 0
    if changed:
        week_end = menu.week_start + timedelta(days=6)
        customer_ids = set((await db.execute(
            select(Subscription.customer_id)
            .join(SubscriptionMealSlot, SubscriptionMealSlot.subscription_id == Subscription.id)
            .where(Subscription.status == SubscriptionStatus.ACTIVE,
                   SubscriptionMealSlot.status == SlotStatus.SCHEDULED,
                   SubscriptionMealSlot.service_date.between(menu.week_start, week_end))
        )).scalars().all())
        for cid in customer_ids:
            db.add(InboxItem(customer_id=cid, kind="MENU_CHANGED",
                             title="This week's menu has changed",
                             body=f"The menu for the week of {menu.week_start:%d %b %Y} was updated."))
        notified = len(customer_ids)
    audit(db, actor_id, "menu.published", "weekly_menu", menu.id,
          data={"version": menu.published_version, "notified_customers": notified})
    return notified


async def published_menu(db: AsyncSession, week_start: date) -> Optional[WeeklyMenu]:
    menu = (await db.execute(select(WeeklyMenu).where(WeeklyMenu.week_start == week_start))).scalars().first()
    return menu if menu is not None and menu.published_version > 0 else None
