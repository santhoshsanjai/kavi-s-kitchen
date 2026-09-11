from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"


# Permissions mapping for quick RBAC reference
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [
        "view_dashboard", "manage_admins", "manage_drivers", "manage_users",
        "manage_customers", "manage_meal_plans", "manage_orders", "assign_drivers",
        "view_live_tracking", "view_reports", "manage_settings", "view_audit_logs"
    ],
    UserRole.ADMIN: [
        "view_dashboard", "manage_customers", "record_enquiries", "manage_meal_plans",
        "create_orders", "assign_drivers", "view_live_tracking", "view_reports"
    ],
    UserRole.DRIVER: [
        "view_assigned_deliveries", "start_delivery", "share_live_location",
        "mark_delivered", "mark_failed", "view_customer_navigation"
    ]
}


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.ADMIN
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    identifier: str = Field(..., description="Username, email, or phone number")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    role: str
    permissions: List[str]


class TokenRefreshRequest(BaseModel):
    refresh_token: str
