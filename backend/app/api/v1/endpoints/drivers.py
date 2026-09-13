from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.schemas.user import UserRole
from app.core import database
from app.models.user import user_helper
from app.api.deps import require_roles, get_current_active_user

router = APIRouter()

admin_access = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])


class DriverStatusUpdate(BaseModel):
    driving_status: str  # AVAILABLE, ON_DELIVERY, OFFLINE, PAUSED


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


@router.patch("/{driver_id}/status", response_model=dict)
async def update_driver_status(
    driver_id: str,
    status_in: DriverStatusUpdate,
    current_user: dict = Depends(get_current_active_user)
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
