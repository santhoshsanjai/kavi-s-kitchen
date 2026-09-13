import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection
from app.db.init_db import init_db


@pytest.mark.asyncio
async def test_order_planning_and_delivery_assignment():
    await connect_to_mongo()
    await init_db()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Login as Kitchen Admin
            login_res = await ac.post(
                "/api/v1/auth/login",
                json={"identifier": "kitchenadmin", "password": "Kitchen@123"},
            )
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # 2. Generate daily orders for today
            gen_res = await ac.post(
                "/api/v1/orders/generate-daily",
                json={"date": today_str},
                headers=headers
            )
            assert gen_res.status_code == 200
            gen_data = gen_res.json()
            assert "generated_count" in gen_data
            assert gen_data["date"] == today_str

            # 3. Fetch orders for today
            orders_res = await ac.get(
                f"/api/v1/orders?date={today_str}",
                headers=headers
            )
            assert orders_res.status_code == 200
            orders_data = orders_res.json()
            assert "items" in orders_data
            assert "summary" in orders_data
            assert len(orders_data["items"]) >= 1

            first_order = orders_data["items"][0]
            first_order_id = first_order["id"]

            # 4. Update single order status to READY
            status_res = await ac.patch(
                f"/api/v1/orders/{first_order_id}/status",
                json={"status": "READY"},
                headers=headers
            )
            assert status_res.status_code == 200
            assert status_res.json()["status"] == "READY"

            # 5. Fetch drivers
            drivers_res = await ac.get("/api/v1/drivers", headers=headers)
            assert drivers_res.status_code == 200
            drivers = drivers_res.json()
            assert len(drivers) >= 1
            driver = drivers[0]
            driver_id = driver["id"]
            driver_name = driver["full_name"]

            # 6. Bulk assign orders to driver
            assign_payload = {
                "driver_id": driver_id,
                "driver_name": driver_name,
                "assignments": [
                    {"order_id": first_order_id, "sequence_number": 1}
                ]
            }
            assign_res = await ac.post(
                "/api/v1/orders/bulk-assign",
                json=assign_payload,
                headers=headers
            )
            assert assign_res.status_code == 200
            assert assign_res.json()["assigned_count"] >= 1

            # Verify order is now ASSIGNED with driver
            updated_order_res = await ac.get(f"/api/v1/orders/{first_order_id}", headers=headers)
            assert updated_order_res.status_code == 200
            updated_order = updated_order_res.json()
            assert updated_order["status"] == "ASSIGNED"
            assert updated_order["assigned_driver_id"] == driver_id
            assert updated_order["sequence_number"] == 1
    finally:
        await close_mongo_connection()
