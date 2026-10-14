import uuid
from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, user_helper
from app.schemas.user import UserRole

security = HTTPBearer(auto_error=False)

ADMIN_ROLES = [UserRole.SUPER_ADMIN, UserRole.ADMIN]


def parse_uuid(value: str, not_found: str = "Not found") -> uuid.UUID:
    """Path IDs that are not valid UUIDs cannot exist, so they are a 404 rather than a 422."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)


async def get_user_from_token(db: AsyncSession, token: Optional[str]) -> Optional[User]:
    """Returns the active user for a valid access token, or None."""
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user_obj(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or not credentials.credentials:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise credentials_exception
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return user


async def get_current_active_user(user: User = Depends(get_current_user_obj)) -> Dict[str, Any]:
    return user_helper(user)


def require_roles(allowed_roles: List[str]):
    """Dependency factory that validates current user role against allowed roles."""
    async def role_checker(
        current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


def is_admin(user: Dict[str, Any]) -> bool:
    return user.get("role") in ADMIN_ROLES
