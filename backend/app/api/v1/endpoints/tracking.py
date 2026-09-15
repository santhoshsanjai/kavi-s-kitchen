from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
import json
import logging

from app.services.tracking_manager import tracking_manager
from app.core import database
from app.api.deps import get_current_active_user, require_roles
from app.schemas.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/driver/{driver_id}")
async def websocket_driver_tracking(websocket: WebSocket, driver_id: str):
    """
    WebSocket connection endpoint for drivers on active shifts/deliveries.
    Receives continuous GPS coordinates: { latitude, longitude, speed, heading, active_order_id }.
    Persists latest location in MongoDB and broadcasts to connected admin dashboards.
    """
    await tracking_manager.connect_driver(driver_id, websocket)

    # Fetch driver basic info
    driver_name = "Driver"
    if database.db is not None:
        try:
            doc = await database.db.users.find_one({"_id": ObjectId(driver_id)})
            if doc:
                driver_name = doc.get("full_name", doc.get("username", "Driver"))
        except Exception:
            pass

    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                lat = float(data.get("latitude", 0.0))
                lng = float(data.get("longitude", 0.0))
                speed = data.get("speed")
                heading = data.get("heading")
                active_order_id = data.get("active_order_id")

                driver_data = {
                    "driver_id": driver_id,
                    "driver_name": driver_name,
                    "latitude": lat,
                    "longitude": lng,
                    "speed": speed,
                    "heading": heading,
                    "driving_status": data.get("driving_status", "ON_DELIVERY"),
                    "active_order_id": active_order_id,
                    "customer_name": data.get("customer_name"),
                    "destination_lat": data.get("destination_lat"),
                    "destination_lng": data.get("destination_lng"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                # Update memory cache and broadcast to admin clients
                await tracking_manager.record_driver_location(driver_id, driver_data)

                # Persist latest location to User profile in MongoDB
                if database.db is not None:
                    try:
                        await database.db.users.update_one(
                            {"_id": ObjectId(driver_id)},
                            {
                                "$set": {
                                    "last_latitude": lat,
                                    "last_longitude": lng,
                                    "last_location_time": datetime.now(timezone.utc),
                                    "driving_status": data.get("driving_status", "ON_DELIVERY")
                                }
                            }
                        )
                    except Exception as db_err:
                        logger.warning(f"Could not persist driver GPS to db: {db_err}")

            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON from driver {driver_id}: {text}")
            except Exception as e:
                logger.error(f"Error handling GPS message from driver {driver_id}: {e}")

    except WebSocketDisconnect:
        tracking_manager.disconnect_driver(driver_id)
        # Broadcast offline notification
        offline_event = {
            "event": "DRIVER_DISCONNECTED",
            "driver_id": driver_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await tracking_manager.broadcast_to_admins(offline_event)


@router.websocket("/ws/admin")
async def websocket_admin_live_stream(websocket: WebSocket):
    """
    WebSocket connection endpoint for Admins on the Live Tracking Map.
    Streams real-time updates of driver coordinates and status changes without polling.
    """
    await tracking_manager.connect_admin(websocket)
    try:
        while True:
            # Admins mainly listen, but handle any ping/message
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        tracking_manager.disconnect_admin(websocket)


@router.get("/live-drivers", response_model=List[Dict[str, Any]])
async def get_live_drivers(
    _: dict = Depends(get_current_active_user)
):
    """
    HTTP REST endpoint returning current positions and status of all active drivers.
    Combines in-memory tracking manager positions with MongoDB user profiles.
    """
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    # Get list of all driver profiles from DB
    cursor = database.db.users.find({"role": UserRole.DRIVER, "is_active": True})
    results = []
    
    # In-memory live positions
    active_memory_map = {loc["driver_id"]: loc for loc in tracking_manager.get_all_active_locations()}

    async for doc in cursor:
        driver_id = str(doc["_id"])
        live_info = active_memory_map.get(driver_id, {})

        # Find current active order if any (status OUT_FOR_DELIVERY)
        active_order = await database.db.orders.find_one({
            "assigned_driver_id": driver_id,
            "status": "OUT_FOR_DELIVERY"
        })

        # Coordinates fallback to doc's last known or default Chennai center
        lat = live_info.get("latitude") or doc.get("last_latitude", 13.0827)
        lng = live_info.get("longitude") or doc.get("last_longitude", 80.2707)

        destination_info = None
        if active_order and active_order.get("delivery_address"):
            addr = active_order.get("delivery_address", {})
            destination_info = {
                "order_id": str(active_order["_id"]),
                "customer_name": active_order.get("customer_name"),
                "customer_phone": active_order.get("customer_phone"),
                "area": addr.get("area"),
                "address_line": addr.get("address_line"),
                "latitude": addr.get("latitude"),
                "longitude": addr.get("longitude"),
                "meal_session": active_order.get("meal_session"),
                "quantity": active_order.get("quantity", 1)
            }

        results.append({
            "driver_id": driver_id,
            "driver_name": doc.get("full_name", doc.get("username", "Driver")),
            "phone": doc.get("phone", ""),
            "vehicle_type": doc.get("vehicle_type", "Motorcycle"),
            "vehicle_number": doc.get("vehicle_number", "TN-01-AB-1234"),
            "driving_status": live_info.get("driving_status") or doc.get("driving_status", "AVAILABLE"),
            "is_connected": driver_id in tracking_manager.driver_sockets,
            "latitude": lat,
            "longitude": lng,
            "speed": live_info.get("speed", 0),
            "heading": live_info.get("heading", 0),
            "last_updated": live_info.get("timestamp") or (doc["last_location_time"].isoformat() if doc.get("last_location_time") else None),
            "active_order": destination_info
        })

    return results
