import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.schemas.user import (
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    ROLE_PERMISSIONS,
)
from app.core.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import User, user_helper
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    identifier = login_data.identifier.strip()

    # Allow logging in via username, email, or phone
    user = (await db.execute(
        select(User).where(or_(
            User.username == identifier,
            User.email == identifier.lower(),
            User.phone == identifier,
        ))
    )).scalars().first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, email, phone, or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your administrator."
        )

    role = user.role.value
    return {
        "access_token": create_access_token(subject=str(user.id), role=role),
        "refresh_token": create_refresh_token(subject=str(user.id), role=role),
        "token_type": "bearer",
        "user": user_helper(user),
        "role": role,
        "permissions": ROLE_PERMISSIONS.get(user.role, []),
    }


@router.post("/refresh")
async def refresh_token(token_request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(token_request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or exists"
        )

    return {
        "access_token": create_access_token(subject=str(user.id), role=user.role.value),
        "token_type": "bearer"
    }


@router.get("/me")
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    role = current_user.get("role")
    return {
        "user": current_user,
        "role": role,
        "permissions": ROLE_PERMISSIONS.get(role, [])
    }


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    return {"message": "Successfully logged out"}
