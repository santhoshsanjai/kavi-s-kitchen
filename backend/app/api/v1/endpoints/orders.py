import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderStatusUpdate,
    CompleteDeliveryRequest,
    FailDeliveryRequest,
    BulkStatusUpdate,
    BulkAssignDriver,
    GenerateDailyOrdersRequest,
    OrderResponse,
    OrdersListResponse,
    DailySummary,
    SessionStats,
    OrderStatus,
    OrderType,
    MealSession,
    DietType
)
from app.schemas.customer import SpiceLevel
from app.schemas.user import UserRole
from app.core.database import get_db
from app.core.time import business_today, parse_date, utcnow
from app.models.customer import Customer
from app.models.order import Order, order_helper
from app.models.user import User
from app.api.deps import ADMIN_ROLES, get_current_active_user, is_admin, parse_uuid, require_roles
from app.services.tracking_manager import tracking_manager

router = APIRouter()

admin_access = require_roles(ADMIN_ROLES)

# States from which a driver may still act on a delivery
PRE_DELIVERY_STATES = {
    OrderStatus.PLANNED, OrderStatus.CONFIRMED, OrderStatus.PREPARING,
    OrderStatus.READY, OrderStatus.ASSIGNED,
}


def _parse_date_or_400(value: str):
    try:
        return parse_date(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date must be in YYYY-MM-DD format")


async def _get_order_or_404(db: AsyncSession, order_id: str, for_update: bool = False) -> Order:
    query = select(Order).where(Order.id == parse_uuid(order_id, "Order not found"))
    if for_update:
        query = query.with_for_update()
    order = (await db.execute(query)).scalars().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


async def _get_assigned_order(db: AsyncSession, order_id: str, current_user: dict) -> Order:
    """Locks the order and checks the caller is the driver it is assigned to."""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if str(order.assigned_driver_id) != current_user["id"]:
        # Same response as a missing order so drivers cannot probe other drivers' orders
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


async def _set_driver_status(db: AsyncSession, driver_id: str, driving_status: str) -> None:
    await db.execute(update(User).where(User.id == uuid.UUID(driver_id)).values(driving_status=driving_status))


async def _release_driver_if_idle(db: AsyncSession, driver_id: str, order: Order) -> None:
    remaining_active = await db.scalar(
        select(func.count()).select_from(Order).where(
            Order.assigned_driver_id == uuid.UUID(driver_id),
            Order.order_date == order.order_date,
            Order.status == OrderStatus.OUT_FOR_DELIVERY,
        )
    )
    if remaining_active == 0:
        await _set_driver_status(db, driver_id, "AVAILABLE")


@router.get("", response_model=OrdersListResponse)
async def get_orders(
    date: Optional[str] = None,
    meal_session: Optional[MealSession] = None,
    status_filter: Optional[OrderStatus] = None,
    driver_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    target_date = _parse_date_or_400(date) if date else business_today()
    day_filters = [Order.order_date == target_date]

    # Drivers only ever see their own assigned orders, including in the summary counts
    if current_user.get("role") == UserRole.DRIVER:
        day_filters.append(Order.assigned_driver_id == uuid.UUID(current_user["id"]))
    elif driver_id:
        day_filters.append(Order.assigned_driver_id == parse_uuid(driver_id, "Driver not found"))

    filters = list(day_filters)
    if meal_session:
        filters.append(Order.meal_session == meal_session)
    if status_filter:
        filters.append(Order.status == status_filter)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(
            Order.customer_name.ilike(pattern),
            Order.customer_phone.ilike(pattern),
            Order.delivery_address["area"].astext.ilike(pattern),
        ))

    items = (await db.execute(
        select(Order).where(*filters).order_by(Order.sequence_number.asc().nulls_last(), Order.customer_name)
    )).scalars().all()

    all_day_orders = (await db.execute(select(Order).where(*day_filters))).scalars().all()

    summary = DailySummary(
        date=target_date.isoformat(),
        total_orders=len(all_day_orders),
        breakfast=SessionStats(),
        lunch=SessionStats(),
        dinner=SessionStats()
    )
    session_stats = {
        MealSession.BREAKFAST: summary.breakfast,
        MealSession.LUNCH: summary.lunch,
        MealSession.DINNER: summary.dinner,
    }
    for o in all_day_orders:
        stat_target = session_stats.get(o.meal_session)
        if stat_target is None:
            continue
        stat_target.total += 1
        if o.diet_type == DietType.VEG:
            stat_target.veg += 1
        else:
            stat_target.non_veg += 1
        if o.status == OrderStatus.READY:
            stat_target.ready += 1
        elif o.status == OrderStatus.DELIVERED:
            stat_target.delivered += 1

    return OrdersListResponse(
        items=[order_helper(o) for o in items],
        total=len(items),
        summary=summary
    )


@router.post("/generate-daily", response_model=dict)
async def generate_daily_orders(
    req: GenerateDailyOrdersRequest,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    target_date = _parse_date_or_400(req.date)
    customers = (await db.execute(select(Customer).where(Customer.is_active.is_(True)))).scalars().all()

    generated_count = 0
    existing_count = 0

    for cust in customers:
        pref = cust.meal_preference or {}
        for session in pref.get("sessions", [MealSession.LUNCH.value]):
            # The partial unique index makes this idempotent, even for concurrent requests
            result = await db.execute(
                insert(Order).values(
                    id=uuid.uuid4(),
                    order_date=target_date,
                    customer_id=cust.id,
                    customer_name=cust.name,
                    customer_phone=cust.phone,
                    delivery_address=cust.address or {},
                    meal_session=MealSession(session),
                    diet_type=DietType(pref.get("diet_type", DietType.VEG.value)),
                    quantity=1,
                    order_type=OrderType.SUBSCRIPTION,
                    spice_level=SpiceLevel(pref.get("spice_level", SpiceLevel.NORMAL.value)),
                    rice_preference=pref.get("rice_preference"),
                    special_notes=pref.get("food_exclusions"),
                    status=OrderStatus.PLANNED,
                    delivery_notes=pref.get("delivery_instructions"),
                ).on_conflict_do_nothing(
                    index_elements=[Order.customer_id, Order.order_date, Order.meal_session],
                    index_where=Order.order_type == OrderType.SUBSCRIPTION,
                ).returning(Order.id)
            )
            if result.scalar_one_or_none() is None:
                existing_count += 1
            else:
                generated_count += 1

    await db.commit()
    return {
        "message": f"Generated {generated_count} new meal occurrences for {target_date.isoformat()}",
        "date": target_date.isoformat(),
        "generated_count": generated_count,
        "existing_count": existing_count
    }


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    data = order_in.model_dump(mode="json")
    try:
        data["customer_id"] = uuid.UUID(data["customer_id"])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown customer")
    if not await db.get(Customer, data["customer_id"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown customer")
    if data.get("assigned_driver_id"):
        data["assigned_driver_id"] = parse_uuid(data["assigned_driver_id"], "Driver not found")
    data["order_date"] = _parse_date_or_400(data["order_date"])

    order = Order(**data)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order_helper(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(db, order_id)
    if not is_admin(current_user) and str(order.assigned_driver_id) != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order_helper(order)


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    order_in: OrderUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(db, order_id)
    update_data = {k: v for k, v in order_in.model_dump(mode="json", exclude_unset=True).items() if v is not None}
    if "assigned_driver_id" in update_data:
        update_data["assigned_driver_id"] = parse_uuid(update_data["assigned_driver_id"], "Driver not found")
    for field, value in update_data.items():
        setattr(order, field, value)
    await db.commit()
    await db.refresh(order)
    return order_helper(order)


@router.patch("/bulk-status", response_model=dict)
async def bulk_update_status(
    bulk_in: BulkStatusUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    ids = []
    for oid in bulk_in.order_ids:
        try:
            ids.append(uuid.UUID(oid))
        except ValueError:
            pass

    res = await db.execute(update(Order).where(Order.id.in_(ids)).values(status=bulk_in.status))
    await db.commit()
    return {
        "message": f"Updated status to '{bulk_in.status.value}' for {res.rowcount} orders",
        "modified_count": res.rowcount
    }


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_in: OrderStatusUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(db, order_id)
    order.status = status_in.status
    if status_in.reason:
        order.status_reason = status_in.reason
    await db.commit()
    await db.refresh(order)
    return order_helper(order)


@router.post("/bulk-assign", response_model=dict)
async def bulk_assign_driver(
    assign_in: BulkAssignDriver,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    driver = await db.get(User, parse_uuid(assign_in.driver_id, "Driver not found"))
    if not driver or driver.role != UserRole.DRIVER or not driver.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    assigned_count = 0
    for item in assign_in.assignments:
        try:
            order_uuid = uuid.UUID(item.order_id)
        except ValueError:
            continue
        res = await db.execute(
            update(Order).where(Order.id == order_uuid).values(
                assigned_driver_id=driver.id,
                assigned_driver_name=driver.full_name,
                sequence_number=item.sequence_number,
                status=OrderStatus.ASSIGNED,
            )
        )
        assigned_count += res.rowcount

    await db.commit()
    return {
        "message": f"Successfully assigned {assigned_count} deliveries to {driver.full_name}",
        "assigned_count": assigned_count
    }


@router.delete("/{order_id}", response_model=dict)
async def delete_order(
    order_id: str,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(db, order_id)
    await db.delete(order)
    await db.commit()
    return {"message": "Order removed successfully", "id": order_id}


@router.post("/{order_id}/start-delivery", response_model=OrderResponse)
async def start_delivery(
    order_id: str,
    current_user: dict = Depends(require_roles([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Assigned driver clicks 'START DELIVERY'.
    Sets status to OUT_FOR_DELIVERY and updates driver status to ON_DELIVERY.
    Broadcasts live event to admin dashboard.
    """
    order = await _get_assigned_order(db, order_id, current_user)
    if order.status == OrderStatus.OUT_FOR_DELIVERY:
        return order_helper(order)  # repeated tap: no change
    if order.status not in PRE_DELIVERY_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start a delivery that is {order.status.value}"
        )

    driver_id = current_user["id"]
    now_utc = utcnow()
    order.status = OrderStatus.OUT_FOR_DELIVERY
    order.out_for_delivery_at = now_utc
    await _set_driver_status(db, driver_id, "ON_DELIVERY")
    await db.commit()
    await db.refresh(order)

    await tracking_manager.broadcast_to_admins({
        "event": "ORDER_OUT_FOR_DELIVERY",
        "data": {
            "order_id": order_id,
            "driver_id": driver_id,
            "driver_name": current_user.get("full_name", current_user.get("username")),
            "customer_name": order.customer_name,
            "delivery_address": order.delivery_address or {},
            "timestamp": now_utc.isoformat()
        }
    })

    return order_helper(order)


@router.post("/{order_id}/complete-delivery", response_model=OrderResponse)
async def complete_delivery(
    order_id: str,
    payload: CompleteDeliveryRequest,
    current_user: dict = Depends(require_roles([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Assigned driver completes delivery with recipient name and optional delivery note.
    Repeating the call on a delivered order changes nothing, so it cannot be completed twice.
    """
    order = await _get_assigned_order(db, order_id, current_user)
    if order.status == OrderStatus.DELIVERED:
        return order_helper(order)
    if order.status != OrderStatus.OUT_FOR_DELIVERY and order.status not in PRE_DELIVERY_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot complete a delivery that is {order.status.value}"
        )

    driver_id = current_user["id"]
    now_utc = utcnow()
    order.status = OrderStatus.DELIVERED
    order.delivered_at = now_utc
    if payload.recipient_name:
        order.recipient_name = payload.recipient_name
    if payload.delivery_note:
        order.delivery_notes = payload.delivery_note
    if payload.proof_photo_url:
        order.proof_photo_url = payload.proof_photo_url
    await db.flush()
    await _release_driver_if_idle(db, driver_id, order)
    await db.commit()
    await db.refresh(order)

    await tracking_manager.broadcast_to_admins({
        "event": "ORDER_DELIVERED",
        "data": {
            "order_id": order_id,
            "driver_id": driver_id,
            "driver_name": current_user.get("full_name", current_user.get("username")),
            "recipient_name": payload.recipient_name,
            "timestamp": now_utc.isoformat()
        }
    })

    return order_helper(order)


@router.post("/{order_id}/fail-delivery", response_model=OrderResponse)
async def fail_delivery(
    order_id: str,
    payload: FailDeliveryRequest,
    current_user: dict = Depends(require_roles([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Assigned driver marks delivery as failed with required structured reason and optional note.
    """
    order = await _get_assigned_order(db, order_id, current_user)
    if order.status == OrderStatus.FAILED:
        return order_helper(order)
    if order.status != OrderStatus.OUT_FOR_DELIVERY and order.status not in PRE_DELIVERY_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fail a delivery that is {order.status.value}"
        )

    driver_id = current_user["id"]
    now_utc = utcnow()
    order.status = OrderStatus.FAILED
    order.status_reason = payload.reason
    order.delivery_notes = payload.notes
    order.failed_at = now_utc
    await db.flush()
    await _release_driver_if_idle(db, driver_id, order)
    await db.commit()
    await db.refresh(order)

    await tracking_manager.broadcast_to_admins({
        "event": "ORDER_FAILED",
        "data": {
            "order_id": order_id,
            "driver_id": driver_id,
            "reason": payload.reason,
            "notes": payload.notes,
            "timestamp": now_utc.isoformat()
        }
    })

    return order_helper(order)
