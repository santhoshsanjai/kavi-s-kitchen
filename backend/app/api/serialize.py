import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import inspect


def jsonable(value: Any) -> Any:
    """Plain JSON values for API output. Money and distances (NUMERIC) become numbers."""
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def row(obj: Any, exclude: Iterable[str] = (), **extra: Any) -> Optional[Dict[str, Any]]:
    """Serializes every mapped column of an ORM row, plus any extra fields."""
    if obj is None:
        return None
    skip = set(exclude)
    data = {c.key: jsonable(getattr(obj, c.key)) for c in inspect(obj).mapper.column_attrs if c.key not in skip}
    data.update({k: jsonable(v) for k, v in extra.items()})
    return data
