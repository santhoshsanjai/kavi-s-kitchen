import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.main import app
from app.core import database
from app.schemas.user import UserRole
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_driver_delivery_flow_and_tracking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Create a Driver user in the DB
        driver_doc = {
            "username": "trackdriver",
            "email": "trackdriver@kaviskitchen.com",
            "hashed_password": get_password_hash("driver123"),
            "full_name": "Test Driver Suresh",
            "phone": "9876543210",
            "role": UserRole.DRIVER,
            "is_active": True,
            "driving_status": "AVAILABLE",
            "vehicle_type": "Motorcycle",
            "vehicle_number": "TN-09-XY-9999",
            "last_latitude": 13.0827,
            "last_longitude": 80.2707,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await database.db.users.delete_many({"username": "trackdriver"})
        res = await database.db.users.insert_one(driver_doc)
        driver_id = str(res.inserted_id)

        # 2. Login as driver
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": "trackdriver",
            "password": "driver123"
        })
        assert login_res.status_code == 200
        driver_token = login_res.json()["access_token"]
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        # 3. Create an order assigned to this driver
        order_doc = {
            "order_date": today_str,
            "customer_id": "cust_123",
            "customer_name": "Rajesh Kannan",
            "customer_phone": "9840112233",
            "delivery_address": {
                "address_line": "Flat 4B, Ruby Towers",
                "area": "Anna Nagar",
                "city": "Chennai",
                "pincode": "600040",
                "latitude": 13.0850,
                "longitude": 80.2100
            },
            "meal_session": "LUNCH",
            "diet_type": "VEG",
            "quantity": 1,
            "order_type": "SUBSCRIPTION",
            "spice_level": "NORMAL",
            "status": "ASSIGNED",
            "assigned_driver_id": driver_id,
            "assigned_driver_name": "Test Driver Suresh",
            "sequence_number": 1,
            "delivery_charge": 0.0,
            "total_price": 180.0,
            "created_at": datetime.now(timezone.utc)
        }
        order_res = await database.db.orders.insert_one(order_doc)
        order_id = str(order_res.inserted_id)

        # 4. Driver fetches /me/today-deliveries
        today_res = await ac.get("/api/v1/drivers/me/today-deliveries", headers=driver_headers)
        assert today_res.status_code == 200
        today_data = today_res.json()
        assert today_data["driver_id"] == driver_id
        assert today_data["total_assigned"] >= 1
        assert any(o["id"] == order_id for o in today_data["orders"])

        # 5. Driver starts delivery
        start_res = await ac.post(f"/api/v1/orders/{order_id}/start-delivery", headers=driver_headers)
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "OUT_FOR_DELIVERY"

        # Check driver status updated to ON_DELIVERY
        driver_db = await database.db.users.find_one({"_id": res.inserted_id})
        assert driver_db["driving_status"] == "ON_DELIVERY"

        # 6. Check live-drivers tracking endpoint
        tracking_res = await ac.get("/api/v1/tracking/live-drivers", headers=driver_headers)
        assert tracking_res.status_code == 200
        live_drivers = tracking_res.json()
        tracked = next((d for d in live_drivers if d["driver_id"] == driver_id), None)
        assert tracked is not None
        assert tracked["driving_status"] == "ON_DELIVERY"
        assert tracked["active_order"] is not None
        assert tracked["active_order"]["customer_name"] == "Rajesh Kannan"

        # 7. Driver completes delivery
        complete_res = await ac.post(
            f"/api/v1/orders/{order_id}/complete-delivery",
            headers=driver_headers,
            json={
                "recipient_name": "Rajesh K.",
                "delivery_note": "Delivered to security desk"
            }
        )
        assert complete_res.status_code == 200
        assert complete_res.json()["status"] == "DELIVERED"

        # Driver should be back to AVAILABLE since no orders are remaining
        driver_db = await database.db.users.find_one({"_id": res.inserted_id})
        assert driver_db["driving_status"] == "AVAILABLE"
