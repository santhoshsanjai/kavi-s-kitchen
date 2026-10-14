import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.schemas.order import OrderStatus
from app.schemas.user import UserRole
from app.core.database import get_db
from app.core.time import business_today, utcnow
from app.models.order import Order, order_helper
from app.models.user import User
from app.api.deps import ADMIN_ROLES, parse_uuid, require_roles
from app.services.tracking_manager import tracking_manager

router = APIRouter()

admin_access = require_roles(ADMIN_ROLES)
driver_access = require_roles([UserRole.DRIVER])


class DriverStatusUpdate(BaseModel):
    driving_status: str  # AVAILABLE, ON_DELIVERY, OFFLINE, PAUSED


class DriverProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    driving_status: Optional[str] = None
    is_active: Optional[bool] = None


class DriverDetailResponse(BaseModel):
    id: str
    username: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str
    is_active: bool
    driving_status: str = "AVAILABLE"
    vehicle_type: Optional[str] = "Motorcycle"
    vehicle_number: Optional[str] = "TN-01-AB-1234"
    assigned_deliveries_count: int = 0
    completed_today_count: int = 0
    last_latitude: Optional[float] = 13.0850
    last_longitude: Optional[float] = 80.2150
    last_location_time: Optional[datetime] = None


class DriverTodayDeliveriesResponse(BaseModel):
    driver_id: str
    driver_name: str
    driving_status: str
    date: str
    total_assigned: int
    pending_count: int
    out_for_delivery_count: int
    completed_count: int
    failed_count: int
    orders: List[Dict[str, Any]]


@router.get("", response_model=List[DriverDetailResponse])
async def list_drivers(
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    today = business_today()
    drivers = (await db.execute(
        select(User).where(User.role == UserRole.DRIVER, User.is_active.is_(True)).order_by(User.full_name)
    )).scalars().all()

    async def count_today(driver_id: uuid.UUID, statuses: List[OrderStatus]) -> int:
        return await db.scalar(
            select(func.count()).select_from(Order).where(
                Order.assigned_driver_id == driver_id,
                Order.order_date == today,
                Order.status.in_(statuses),
            )
        )

    results = []
    for doc in drivers:
        results.append(DriverDetailResponse(
            id=str(doc.id),
            username=doc.username,
            full_name=doc.full_name,
            phone=doc.phone,
            email=doc.email,
            role=doc.role.value,
            is_active=doc.is_active,
            driving_status=doc.driving_status,
            vehicle_type=doc.vehicle_type,
            vehicle_number=doc.vehicle_number,
            assigned_deliveries_count=await count_today(doc.id, [OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY]),
            completed_today_count=await count_today(doc.id, [OrderStatus.DELIVERED]),
            last_latitude=doc.last_latitude,
            last_longitude=doc.last_longitude,
            last_location_time=doc.last_location_time
        ))
    return results


@router.get("/me/today-deliveries", response_model=DriverTodayDeliveriesResponse)
async def get_my_today_deliveries(
    current_user: dict = Depends(driver_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns today's (Asia/Kolkata) assigned deliveries ordered by sequence_number for the logged-in driver.
    """
    driver_id = current_user["id"]
    driver_name = current_user.get("full_name") or current_user.get("username", "Driver")
    today = business_today()

    rows = (await db.execute(
        select(Order).where(
            Order.assigned_driver_id == uuid.UUID(driver_id),
            Order.order_date == today,
        ).order_by(Order.sequence_number.asc().nulls_last(), Order.created_at)
    )).scalars().all()

    orders = []
    pending_count = 0
    out_for_delivery_count = 0
    completed_count = 0
    failed_count = 0

    for row in rows:
        order = order_helper(row)
        orders.append(order)
        st = order.get("status")
        if st in ["ASSIGNED", "READY", "PREPARING", "CONFIRMED", "PLANNED"]:
            pending_count += 1
        elif st == "OUT_FOR_DELIVERY":
            out_for_delivery_count += 1
        elif st == "DELIVERED":
            completed_count += 1
        elif st == "FAILED":
            failed_count += 1

    return DriverTodayDeliveriesResponse(
        driver_id=driver_id,
        driver_name=driver_name,
        driving_status=current_user.get("driving_status", "AVAILABLE"),
        date=today.isoformat(),
        total_assigned=len(orders),
        pending_count=pending_count,
        out_for_delivery_count=out_for_delivery_count,
        completed_count=completed_count,
        failed_count=failed_count,
        orders=orders
    )


@router.patch("/me/status", response_model=dict)
async def update_my_status(
    status_in: DriverStatusUpdate,
    current_user: dict = Depends(driver_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows authenticated driver to change their shift status (AVAILABLE, ON_DELIVERY, PAUSED, OFFLINE).
    """
    driver_id = current_user["id"]
    driver = await db.get(User, uuid.UUID(driver_id))
    driver.driving_status = status_in.driving_status
    await db.commit()

    # Broadcast to admin live fleet stream
    await tracking_manager.broadcast_to_admins({
        "event": "DRIVER_STATUS_CHANGE",
        "data": {
            "driver_id": driver_id,
            "driver_name": current_user.get("full_name", current_user.get("username")),
            "driving_status": status_in.driving_status,
            "timestamp": utcnow().isoformat()
        }
    })

    return {
        "message": "Status updated successfully",
        "driving_status": status_in.driving_status
    }


async def _get_driver_or_404(db: AsyncSession, driver_id: str) -> User:
    driver = await db.get(User, parse_uuid(driver_id, "Driver not found"))
    # This endpoint group must never edit admin accounts
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


@router.patch("/{driver_id}", response_model=dict)
async def update_driver_profile(
    driver_id: str,
    update_in: DriverProfileUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin endpoint to update driver vehicle info, contact, and active state.
    """
    driver = await _get_driver_or_404(db, driver_id)
    update_fields = {k: v for k, v in update_in.model_dump(exclude_unset=True).items() if v is not None}
    if not update_fields:
        return {"message": "No changes provided"}

    for field, value in update_fields.items():
        setattr(driver, field, value)
    await db.commit()
    return {"message": "Driver profile updated successfully"}


@router.patch("/{driver_id}/status", response_model=dict)
async def update_driver_status_admin(
    driver_id: str,
    status_in: DriverStatusUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    driver = await _get_driver_or_404(db, driver_id)
    driver.driving_status = status_in.driving_status
    await db.commit()
    return {"message": "Driver status updated", "driving_status": status_in.driving_status}
