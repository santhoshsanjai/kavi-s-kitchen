import pytest

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.core.time import business_today
from app.models.customer import Customer
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderStatus, OrderType
from app.schemas.customer import DietType, MealSession
from app.schemas.user import UserRole
from tests.conftest import login


@pytest.mark.asyncio
async def test_driver_delivery_flow_and_tracking(client):
    # 1. Create a driver, a customer and an order assigned to the driver
    async with SessionLocal() as db:
        driver = User(
            username="trackdriver",
            email="trackdriver@kaviskitchen.com",
            hashed_password=get_password_hash("driver123"),
            full_name="Test Driver Suresh",
            phone="9876500000",
            role=UserRole.DRIVER,
            is_active=True,
            driving_status="AVAILABLE",
            vehicle_type="Motorcycle",
            vehicle_number="TN-09-XY-9999",
        )
        customer = Customer(
            name="Rajesh Kannan",
            phone="9840112233",
            address={"address_line": "Flat 4B, Ruby Towers", "area": "Anna Nagar", "city": "Chennai"},
            meal_preference={"diet_type": "VEG", "sessions": ["LUNCH"]},
        )
        db.add_all([driver, customer])
        await db.flush()
        order = Order(
            order_date=business_today(),
            customer_id=customer.id,
            customer_name=customer.name,
            customer_phone=customer.phone,
            delivery_address={
                "address_line": "Flat 4B, Ruby Towers",
                "area": "Anna Nagar",
                "city": "Chennai",
                "pincode": "600040",
                "latitude": 13.0850,
                "longitude": 80.2100,
            },
            meal_session=MealSession.LUNCH,
            diet_type=DietType.VEG,
            order_type=OrderType.SUBSCRIPTION,
            status=OrderStatus.ASSIGNED,
            assigned_driver_id=driver.id,
            assigned_driver_name=driver.full_name,
            sequence_number=1,
            total_price=180,
        )
        db.add(order)
        await db.commit()
        driver_id, order_id = str(driver.id), str(order.id)

    driver_headers = await login(client, "trackdriver", "driver123")
    admin_headers = await login(client, "kitchenadmin", "Kitchen@123")

    # 2. Driver fetches /me/today-deliveries
    today_res = await client.get("/api/v1/drivers/me/today-deliveries", headers=driver_headers)
    assert today_res.status_code == 200
    today_data = today_res.json()
    assert today_data["driver_id"] == driver_id
    assert today_data["total_assigned"] >= 1
    assert any(o["id"] == order_id for o in today_data["orders"])

    # 3. Driver starts delivery
    start_res = await client.post(f"/api/v1/orders/{order_id}/start-delivery", headers=driver_headers)
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "OUT_FOR_DELIVERY"

    async with SessionLocal() as db:
        assert (await db.get(User, driver.id)).driving_status == "ON_DELIVERY"

    # 4. Live-drivers tracking is admin-only
    assert (await client.get("/api/v1/tracking/live-drivers", headers=driver_headers)).status_code == 403
    tracking_res = await client.get("/api/v1/tracking/live-drivers", headers=admin_headers)
    assert tracking_res.status_code == 200
    tracked = next((d for d in tracking_res.json() if d["driver_id"] == driver_id), None)
    assert tracked is not None
    assert tracked["driving_status"] == "ON_DELIVERY"
    assert tracked["active_order"] is not None
    assert tracked["active_order"]["customer_name"] == "Rajesh Kannan"

    # 5. Driver completes delivery
    complete_res = await client.post(
        f"/api/v1/orders/{order_id}/complete-delivery",
        headers=driver_headers,
        json={"recipient_name": "Rajesh K.", "delivery_note": "Delivered to security desk"},
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "DELIVERED"

    # Driver should be back to AVAILABLE since no orders are remaining
    async with SessionLocal() as db:
        assert (await db.get(User, driver.id)).driving_status == "AVAILABLE"

    # 6. Completing again changes nothing (no duplicate completion)
    again = await client.post(f"/api/v1/orders/{order_id}/complete-delivery", headers=driver_headers, json={})
    assert again.status_code == 200
    assert again.json()["status"] == "DELIVERED"
    assert again.json()["updated_at"] == complete_res.json()["updated_at"]

    # 7. A delivered order cannot be marked failed afterwards
    fail_res = await client.post(
        f"/api/v1/orders/{order_id}/fail-delivery", headers=driver_headers, json={"reason": "OTHER"}
    )
    assert fail_res.status_code == 409
