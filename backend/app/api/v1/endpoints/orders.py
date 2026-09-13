from fastapi import APIRouter, HTTPException, status, Depends, Query
from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderStatusUpdate,
    BulkStatusUpdate,
    BulkAssignDriver,
    GenerateDailyOrdersRequest,
    OrderResponse,
    OrdersListResponse,
    DailySummary,
    SessionStats,
    OrderStatus,
    MealSession,
    DietType
)
from app.schemas.user import UserRole
from app.core import database
from app.models.order import order_helper
from app.api.deps import require_roles, get_current_active_user

router = APIRouter()

admin_access = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])


@router.get("", response_model=OrdersListResponse)
async def get_orders(
    date: Optional[str] = None,
    meal_session: Optional[MealSession] = None,
    status_filter: Optional[OrderStatus] = None,
    driver_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    query: Dict[str, Any] = {"order_date": target_date}

    if meal_session:
        query["meal_session"] = meal_session
    if status_filter:
        query["status"] = status_filter
    if driver_id:
        query["assigned_driver_id"] = driver_id

    # If the user is a DRIVER, automatically limit to their assigned orders
    if current_user.get("role") == UserRole.DRIVER:
        driver_uid = current_user.get("id")
        query["assigned_driver_id"] = driver_uid

    if search:
        search_regex = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"customer_name": search_regex},
            {"customer_phone": search_regex},
            {"delivery_address.area": search_regex}
        ]

    orders_collection = database.db.orders
    cursor = orders_collection.find(query).sort([("sequence_number", 1), ("customer_name", 1)])
    
    items = []
    async for doc in cursor:
        items.append(order_helper(doc))

    # Compute daily summary counts across all orders for target_date
    all_day_orders = []
    async for doc in orders_collection.find({"order_date": target_date}):
        all_day_orders.append(doc)

    summary = DailySummary(
        date=target_date,
        total_orders=len(all_day_orders),
        breakfast=SessionStats(),
        lunch=SessionStats(),
        dinner=SessionStats()
    )

    for o in all_day_orders:
        sess = o.get("meal_session")
        diet = o.get("diet_type")
        stat = o.get("status")

        stat_target: Optional[SessionStats] = None
        if sess == MealSession.BREAKFAST:
            stat_target = summary.breakfast
        elif sess == MealSession.LUNCH:
            stat_target = summary.lunch
        elif sess == MealSession.DINNER:
            stat_target = summary.dinner

        if stat_target:
            stat_target.total += 1
            if diet == DietType.VEG:
                stat_target.veg += 1
            else:
                stat_target.non_veg += 1
            if stat == OrderStatus.READY:
                stat_target.ready += 1
            elif stat == OrderStatus.DELIVERED:
                stat_target.delivered += 1

    return OrdersListResponse(
        items=items,
        total=len(items),
        summary=summary
    )


@router.post("/generate-daily", response_model=dict)
async def generate_daily_orders(
    req: GenerateDailyOrdersRequest,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    target_date = req.date.strip()
    customers_cursor = database.db.customers.find({"is_active": True})
    
    generated_count = 0
    existing_count = 0

    async for cust in customers_cursor:
        cust_id = str(cust["_id"])
        pref = cust.get("meal_preference", {})
        sessions = pref.get("sessions", ["LUNCH"])
        diet_type = pref.get("diet_type", "VEG")

        for session in sessions:
            # Check if order already exists for this customer + date + session
            exists = await database.db.orders.find_one({
                "customer_id": cust_id,
                "order_date": target_date,
                "meal_session": session
            })

            if exists:
                existing_count += 1
                continue

            order_doc = {
                "order_date": target_date,
                "customer_id": cust_id,
                "customer_name": cust.get("name", ""),
                "customer_phone": cust.get("phone", ""),
                "delivery_address": cust.get("address", {}),
                "meal_session": session,
                "diet_type": diet_type,
                "quantity": 1,
                "order_type": "SUBSCRIPTION",
                "spice_level": pref.get("spice_level", "NORMAL"),
                "rice_preference": pref.get("rice_preference"),
                "special_notes": pref.get("food_exclusions"),
                "status": OrderStatus.PLANNED,
                "assigned_driver_id": None,
                "assigned_driver_name": None,
                "sequence_number": None,
                "delivery_notes": pref.get("delivery_instructions"),
                "delivery_charge": 0.0,
                "total_price": 0.0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            await database.db.orders.insert_one(order_doc)
            generated_count += 1

    return {
        "message": f"Generated {generated_count} new meal occurrences for {target_date}",
        "date": target_date,
        "generated_count": generated_count,
        "existing_count": existing_count
    }


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    doc = order_in.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)

    result = await database.db.orders.insert_one(doc)
    doc["_id"] = result.inserted_id

    return order_helper(doc)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    _: dict = Depends(get_current_active_user)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(order_id)}
    except Exception:
        query = {"id": order_id}

    order = await database.db.orders.find_one(query)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return order_helper(order)


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    order_in: OrderUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(order_id)}
    except Exception:
        query = {"id": order_id}

    existing = await database.db.orders.find_one(query)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    update_data = {k: v for k, v in order_in.model_dump(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)

    await database.db.orders.update_one(query, {"$set": update_data})
    updated = await database.db.orders.find_one(query)
    return order_helper(updated)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_in: OrderStatusUpdate,
    _: dict = Depends(get_current_active_user)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(order_id)}
    except Exception:
        query = {"id": order_id}

    order = await database.db.orders.find_one(query)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    update_data = {
        "status": status_in.status,
        "updated_at": datetime.now(timezone.utc)
    }
    if status_in.reason:
        update_data["status_reason"] = status_in.reason

    await database.db.orders.update_one(query, {"$set": update_data})
    updated = await database.db.orders.find_one(query)
    return order_helper(updated)


@router.patch("/bulk-status", response_model=dict)
async def bulk_update_status(
    bulk_in: BulkStatusUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    object_ids = []
    for oid in bulk_in.order_ids:
        try:
            object_ids.append(ObjectId(oid))
        except Exception:
            pass

    query = {
        "$or": [
            {"_id": {"$in": object_ids}},
            {"id": {"$in": bulk_in.order_ids}}
        ]
    }

    res = await database.db.orders.update_many(
        query,
        {
            "$set": {
                "status": bulk_in.status,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    return {
        "message": f"Updated status to '{bulk_in.status}' for {res.modified_count} orders",
        "modified_count": res.modified_count
    }


@router.post("/bulk-assign", response_model=dict)
async def bulk_assign_driver(
    assign_in: BulkAssignDriver,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    assigned_count = 0
    for item in assign_in.assignments:
        try:
            query = {"_id": ObjectId(item.order_id)}
        except Exception:
            query = {"id": item.order_id}

        res = await database.db.orders.update_one(
            query,
            {
                "$set": {
                    "assigned_driver_id": assign_in.driver_id,
                    "assigned_driver_name": assign_in.driver_name,
                    "sequence_number": item.sequence_number,
                    "status": OrderStatus.ASSIGNED,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        if res.modified_count > 0:
            assigned_count += 1

    return {
        "message": f"Successfully assigned {assigned_count} deliveries to {assign_in.driver_name}",
        "assigned_count": assigned_count
    }


@router.delete("/{order_id}", response_model=dict)
async def delete_order(
    order_id: str,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(order_id)}
    except Exception:
        query = {"id": order_id}

    result = await database.db.orders.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return {"message": "Order removed successfully", "id": order_id}
