from typing import Dict, List, Optional
import json
import logging
from datetime import datetime, timezone
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TrackingManager:
    """
    Manages real-time WebSocket connections between delivery drivers and admin live-tracking dashboards.
    Maintains an in-memory registry of latest coordinates for quick lookup and broadcasts live updates.
    """

    def __init__(self):
        self.driver_sockets: Dict[str, WebSocket] = {}
        self.admin_sockets: List[WebSocket] = []
        self.latest_locations: Dict[str, dict] = {}

    async def connect_driver(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.driver_sockets[driver_id] = websocket
        logger.info(f"Driver {driver_id} connected for GPS tracking. Total drivers: {len(self.driver_sockets)}")

    def disconnect_driver(self, driver_id: str):
        if driver_id in self.driver_sockets:
            del self.driver_sockets[driver_id]
            logger.info(f"Driver {driver_id} disconnected. Remaining drivers: {len(self.driver_sockets)}")

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_sockets.append(websocket)
        logger.info(f"Admin connected to live tracking stream. Total admin listeners: {len(self.admin_sockets)}")
        
        # Immediately send current state of all active drivers upon connecting
        if self.latest_locations:
            init_message = {
                "event": "INITIAL_FLEET_STATE",
                "drivers": list(self.latest_locations.values()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            try:
                await websocket.send_text(json.dumps(init_message))
            except Exception as e:
                logger.error(f"Error sending initial state to admin: {e}")

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_sockets:
            self.admin_sockets.remove(websocket)
            logger.info(f"Admin disconnected from live tracking stream. Remaining: {len(self.admin_sockets)}")

    async def record_driver_location(self, driver_id: str, data: dict):
        """
        Stores latest driver location and broadcasts update event to all listening admin clients.
        """
        data["driver_id"] = driver_id
        data["updated_at"] = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        self.latest_locations[driver_id] = data

        payload = {
            "event": "DRIVER_LOCATION_UPDATE",
            "data": data
        }
        await self.broadcast_to_admins(payload)

    async def broadcast_to_admins(self, payload: dict):
        dead_sockets = []
        message_str = json.dumps(payload)
        for ws in self.admin_sockets:
            try:
                await ws.send_text(message_str)
            except Exception as e:
                logger.warning(f"Admin websocket send error: {e}, queuing for removal")
                dead_sockets.append(ws)

        for dead in dead_sockets:
            if dead in self.admin_sockets:
                self.admin_sockets.remove(dead)

    def get_all_active_locations(self) -> List[dict]:
        return list(self.latest_locations.values())


# Singleton instance
tracking_manager = TrackingManager()
