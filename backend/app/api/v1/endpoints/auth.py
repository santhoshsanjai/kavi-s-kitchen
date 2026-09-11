from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from typing import Dict, Any

from app.schemas.user import (
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    UserResponse,
    ROLE_PERMISSIONS,
    UserRole
)
from app.core import database
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import user_helper
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    identifier = login_data.identifier.strip()
    
    # Allow logging in via username, email, or phone
    query = {
        "$or": [
            {"username": identifier},
            {"email": identifier.lower()},
            {"phone": identifier}
        ]
    }
    
    user = await database.db.users.find_one(query)
    
    if not user or not verify_password(login_data.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, email, phone, or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your administrator."
        )
        
    user_id_str = str(user["_id"])
    role = user.get("role", UserRole.ADMIN)
    
    access_token = create_access_token(subject=user_id_str, role=role)
    refresh_token = create_refresh_token(subject=user_id_str, role=role)
    
    formatted_user = user_helper(user)
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": formatted_user,
        "role": role,
        "permissions": permissions
    }


@router.post("/refresh")
async def refresh_token(token_request: TokenRefreshRequest):
    payload = decode_token(token_request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
        
    try:
        user = await database.db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await database.db.users.find_one({"id": user_id})
        
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or exists"
        )
        
    role = user.get("role", UserRole.ADMIN)
    new_access_token = create_access_token(subject=user_id, role=role)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    role = current_user.get("role")
    permissions = ROLE_PERMISSIONS.get(role, [])
    return {
        "user": current_user,
        "role": role,
        "permissions": permissions
    }


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    return {"message": "Successfully logged out"}
