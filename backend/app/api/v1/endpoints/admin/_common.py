import uuid
from datetime import date
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status

from app.api.deps import ADMIN_ROLES, require_roles
from app.domain.service_calendar import month_start

admin_access = require_roles(ADMIN_ROLES)


def actor(user: Dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(user["id"])


def parse_month(value: str) -> date:
    """Accepts YYYY-MM or any YYYY-MM-DD in the month."""
    try:
        text = value.strip()
        return month_start(date.fromisoformat(text + "-01" if len(text) == 7 else text))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Month must be YYYY-MM")


def optional_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id")


Admin = Depends(admin_access)
