"""Published weekly menu, readable by any signed-in user (customer app in a later phase)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.services import menu_service

router = APIRouter()


@router.get("/{week_start}")
async def published_menu(week_start: date, _: dict = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    start = menu_service.week_start_of(week_start)
    menu = await menu_service.published_menu(db, start)
    if menu is None:
        return {"week_start": start.isoformat(), "published": False, "version": 0, "entries": []}
    return {"week_start": start.isoformat(), "published": True, "version": menu.published_version,
            "published_at": menu.published_at.isoformat() if menu.published_at else None,
            "entries": [e for e in menu.published_entries if e.get("is_available", True)]}
