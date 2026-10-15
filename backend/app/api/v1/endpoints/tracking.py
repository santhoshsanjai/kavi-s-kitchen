import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import json
import logging

from app.services.tracking_manager import tracking_manager
from app.core.database import SessionLocal, get_db
from app.core.time import utcnow
from app.api.deps import ADMIN_ROLES, get_user_from_token, require_roles
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderStatus
from app.schemas.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

admin_access = require_roles(ADMIN_ROLES)

# Browsers cannot set headers on WebSocket requests, so the access token is passed as ?token=
POLICY_VIOLATION = status.WS_1008_POLICY_VIOLATION


@router.websocket("/ws/driver/{driver_id}")
async def websocket_driver_tracking(websocket: WebSocket, driver_id: str, token: Optional[str] = Query(None)):
    """
    WebSocket connection endpoint for drivers on active shifts/deliveries.
    Only the driver themself may stream positions for their own driver_id.
    Receives continuous GPS coordinates: { latitude, longitude, speed, heading, active_order_id }.
    """
    async with SessionLocal() as db:
        user = await get_user_from_token(db, token)
    if user is None or user.role != UserRole.DRIVER or str(user.id) != driver_id:
        await websocket.close(code=POLICY_VIOLATION)
        return

    driver_uuid = user.id
    driver_name = user.full_name or user.username
    await tracking_manager.connect_driver(driver_id, websocket)

    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                lat = float(data.get("latitude", 0.0))
                lng = float(data.get("longitude", 0.0))
                driving_status = data.get("driving_status", "ON_DELIVERY")

                driver_data = {
                    "driver_id": driver_id,
                    "driver_name": driver_name,
                    "latitude": lat,
                    "longitude": lng,
                    "speed": data.get("speed"),
                    "heading": data.get("heading"),
                    "driving_status": driving_status,
                    "active_order_id": data.get("active_order_id"),
                    "customer_name": data.get("customer_name"),
                    "destination_lat": data.get("destination_lat"),
                    "destination_lng": data.get("destination_lng"),
                    "timestamp": utcnow().isoformat()
                }

                # Update memory cache and broadcast to admin clients
                await tracking_manager.record_driver_location(driver_id, driver_data)

                try:
                    async with SessionLocal() as db:
                        await db.execute(
                            update(User).where(User.id == driver_uuid).values(
                                last_latitude=lat,
                                last_longitude=lng,
                                last_location_time=utcnow(),
                                driving_status=driving_status,
                            )
                        )
                        await db.commit()
                except Exception as db_err:
                    logger.warning(f"Could not persist driver GPS to db: {db_err}")

            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON from driver {driver_id}")
            except Exception as e:
                logger.error(f"Error handling GPS message from driver {driver_id}: {e}")

    except WebSocketDisconnect:
        tracking_manager.disconnect_driver(driver_id)
        await tracking_manager.broadcast_to_admins({
            "event": "DRIVER_DISCONNECTED",
            "driver_id": driver_id,
            "timestamp": utcnow().isoformat()
        })


@router.websocket("/ws/admin")
async def websocket_admin_live_stream(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket connection endpoint for Admins on the Live Tracking Map.
    Streams real-time updates of driver coordinates and status changes without polling.
    """
    async with SessionLocal() as db:
        user = await get_user_from_token(db, token)
    if user is None or user.role not in ADMIN_ROLES:
        await websocket.close(code=POLICY_VIOLATION)
        return

    await tracking_manager.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        tracking_manager.disconnect_admin(websocket)


@router.get("/live-drivers", response_model=List[Dict[str, Any]])
async def get_live_drivers(
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Current positions and status of all active drivers.
    Combines in-memory tracking manager positions with stored driver profiles.
    """
    drivers = (await db.execute(
        select(User).where(User.role == UserRole.DRIVER, User.is_active.is_(True))
    )).scalars().all()

    active_memory_map = {loc["driver_id"]: loc for loc in tracking_manager.get_all_active_locations()}

    results = []
    for doc in drivers:
        driver_id = str(doc.id)
        live_info = active_memory_map.get(driver_id, {})

        active_order = (await db.execute(
            select(Order).where(
                Order.assigned_driver_id == doc.id,
                Order.status == OrderStatus.OUT_FOR_DELIVERY,
            ).limit(1)
        )).scalars().first()

        # Coordinates fall back to last known position, then Chennai centre
        lat = live_info.get("latitude") or doc.last_latitude or 13.0827
        lng = live_info.get("longitude") or doc.last_longitude or 80.2707

        destination_info = None
        if active_order and active_order.delivery_address:
            addr = active_order.delivery_address
            destination_info = {
                "order_id": str(active_order.id),
                "customer_name": active_order.customer_name,
                "customer_phone": active_order.customer_phone,
                "area": addr.get("area"),
                "address_line": addr.get("address_line"),
                "latitude": addr.get("latitude"),
                "longitude": addr.get("longitude"),
                "meal_session": active_order.meal_session.value,
                "quantity": active_order.quantity
            }

        results.append({
            "driver_id": driver_id,
            "driver_name": doc.full_name or doc.username,
            "phone": doc.phone or "",
            "vehicle_type": doc.vehicle_type,
            "vehicle_number": doc.vehicle_number,
            "driving_status": live_info.get("driving_status") or doc.driving_status,
            "is_connected": driver_id in tracking_manager.driver_sockets,
            "latitude": lat,
            "longitude": lng,
            "speed": live_info.get("speed", 0),
            "heading": live_info.get("heading", 0),
            "last_updated": live_info.get("timestamp") or (doc.last_location_time.isoformat() if doc.last_location_time else None),
            "active_order": destination_info
        })

    return results
