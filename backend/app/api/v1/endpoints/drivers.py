from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

from app.schemas.user import UserRole
from app.core import database
from app.models.order import order_helper
from app.api.deps import require_roles, get_current_active_user
from app.services.tracking_manager import tracking_manager

router = APIRouter()

admin_access = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])


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
    current_user: dict = Depends(get_current_active_user)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor = database.db.users.find({"role": UserRole.DRIVER, "is_active": True})
    
    drivers = []
    async for doc in cursor:
        driver_id = str(doc["_id"])
        
        # Count active deliveries today for this driver
        assigned_count = await database.db.orders.count_documents({
            "assigned_driver_id": driver_id,
            "order_date": today_str,
            "status": {"$in": ["ASSIGNED", "OUT_FOR_DELIVERY"]}
        })
        
        completed_count = await database.db.orders.count_documents({
            "assigned_driver_id": driver_id,
            "order_date": today_str,
            "status": "DELIVERED"
        })

        drivers.append(DriverDetailResponse(
            id=driver_id,
            username=doc.get("username", ""),
            full_name=doc.get("full_name", "Driver"),
            phone=doc.get("phone"),
            email=doc.get("email"),
            role=doc.get("role", "DRIVER"),
            is_active=doc.get("is_active", True),
            driving_status=doc.get("driving_status", "AVAILABLE"),
            vehicle_type=doc.get("vehicle_type", "Motorcycle"),
            vehicle_number=doc.get("vehicle_number", "TN-01-AB-1234"),
            assigned_deliveries_count=assigned_count,
            completed_today_count=completed_count,
            last_latitude=doc.get("last_latitude", 13.0850),
            last_longitude=doc.get("last_longitude", 80.2150),
            last_location_time=doc.get("last_location_time")
        ))

    return drivers


@router.get("/me/today-deliveries", response_model=DriverTodayDeliveriesResponse)
async def get_my_today_deliveries(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Returns today's assigned deliveries ordered by sequence_number for the logged-in driver.
    """
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    driver_id = str(current_user["id"])
    driver_name = current_user.get("full_name", current_user.get("username", "Driver"))
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cursor = database.db.orders.find({
        "assigned_driver_id": driver_id,
        "order_date": today_str
    }).sort([("sequence_number", 1), ("created_at", 1)])

    orders = []
    pending_count = 0
    out_for_delivery_count = 0
    completed_count = 0
    failed_count = 0

    async for doc in cursor:
        order = order_helper(doc)
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
        date=today_str,
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
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows authenticated driver to change their shift status (AVAILABLE, ON_DELIVERY, PAUSED, OFFLINE).
    """
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    driver_id = str(current_user["id"])
    try:
        query = {"_id": ObjectId(driver_id)}
    except Exception:
        query = {"id": driver_id}

    await database.db.users.update_one(
        query,
        {
            "$set": {
                "driving_status": status_in.driving_status,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    # Broadcast to admin live fleet stream
    await tracking_manager.broadcast_to_admins({
        "event": "DRIVER_STATUS_CHANGE",
        "data": {
            "driver_id": driver_id,
            "driver_name": current_user.get("full_name", current_user.get("username")),
            "driving_status": status_in.driving_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    })

    return {
        "message": "Status updated successfully",
        "driving_status": status_in.driving_status
    }


@router.patch("/{driver_id}", response_model=dict)
async def update_driver_profile(
    driver_id: str,
    update_in: DriverProfileUpdate,
    _: dict = Depends(admin_access)
):
    """
    Admin endpoint to update driver vehicle info, contact, and active state.
    """
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(driver_id)}
    except Exception:
        query = {"id": driver_id}

    update_fields = {k: v for k, v in update_in.model_dump(exclude_unset=True).items() if v is not None}
    if not update_fields:
        return {"message": "No changes provided"}

    update_fields["updated_at"] = datetime.now(timezone.utc)

    res = await database.db.users.update_one(query, {"$set": update_fields})
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    return {"message": "Driver profile updated successfully"}


@router.patch("/{driver_id}/status", response_model=dict)
async def update_driver_status_admin(
    driver_id: str,
    status_in: DriverStatusUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(driver_id)}
    except Exception:
        query = {"id": driver_id}

    res = await database.db.users.update_one(
        query,
        {
            "$set": {
                "driving_status": status_in.driving_status,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    if res.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )

    return {"message": "Driver status updated", "driving_status": status_in.driving_status}
