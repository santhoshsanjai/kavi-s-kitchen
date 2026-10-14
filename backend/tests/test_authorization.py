"""Backend authorization: drivers only reach their own assigned orders; WebSockets require a valid token."""
import uuid

import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.core.time import business_today
from app.main import app
from app.models.customer import Customer
from app.models.order import Order
from app.models.user import User
from app.schemas.customer import DietType, MealSession
from app.schemas.order import OrderStatus, OrderType
from app.schemas.user import UserRole
from tests.conftest import login


async def _make_driver(db, username: str) -> User:
    driver = User(
        username=username,
        full_name=username.title(),
        hashed_password=get_password_hash("pass1234"),
        role=UserRole.DRIVER,
    )
    db.add(driver)
    await db.flush()
    return driver


@pytest_asyncio.fixture
async def two_drivers_one_order():
    async with SessionLocal() as db:
        owner = await _make_driver(db, "ownerdriver")
        other = await _make_driver(db, "otherdriver")
        customer = Customer(name="Private Customer", phone="9000000001", address={"area": "Adyar"},
                            meal_preference={})
        db.add(customer)
        await db.flush()
        order = Order(
            order_date=business_today(), customer_id=customer.id, customer_name=customer.name,
            customer_phone=customer.phone, delivery_address={"address_line": "1 Beach Road", "area": "Adyar", "city": "Chennai"},
            meal_session=MealSession.LUNCH, diet_type=DietType.VEG, order_type=OrderType.AD_HOC,
            status=OrderStatus.ASSIGNED, assigned_driver_id=owner.id, assigned_driver_name=owner.full_name,
        )
        db.add(order)
        await db.commit()
        return {"owner_id": str(owner.id), "other_id": str(other.id), "order_id": str(order.id)}


@pytest.mark.asyncio
async def test_driver_cannot_read_or_act_on_another_drivers_order(client, two_drivers_one_order):
    order_id = two_drivers_one_order["order_id"]
    other = await login(client, "otherdriver", "pass1234")
    owner = await login(client, "ownerdriver", "pass1234")

    assert (await client.get(f"/api/v1/orders/{order_id}", headers=other)).status_code == 404
    for action, body in [("start-delivery", None), ("complete-delivery", {}), ("fail-delivery", {"reason": "OTHER"})]:
        res = await client.post(f"/api/v1/orders/{order_id}/{action}", headers=other, json=body)
        assert res.status_code == 404, action

    # The other driver's order list excludes it, including the summary counts
    listing = (await client.get("/api/v1/orders", headers=other)).json()
    assert listing["items"] == []
    assert listing["summary"]["total_orders"] == 0

    # The assigned driver can read it
    assert (await client.get(f"/api/v1/orders/{order_id}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_driver_cannot_use_admin_endpoints(client, two_drivers_one_order):
    order_id = two_drivers_one_order["order_id"]
    owner = await login(client, "ownerdriver", "pass1234")

    res = await client.patch(f"/api/v1/orders/{order_id}/status", headers=owner, json={"status": "DELIVERED"})
    assert res.status_code == 403
    assert (await client.get("/api/v1/drivers", headers=owner)).status_code == 403
    assert (await client.get("/api/v1/customers", headers=owner)).status_code == 403
    assert (await client.get("/api/v1/tracking/live-drivers", headers=owner)).status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_edit_admin_accounts_through_driver_endpoints(client):
    admin = await login(client, "kitchenadmin", "Kitchen@123")
    me = (await client.get("/api/v1/auth/me", headers=admin)).json()["user"]
    res = await client.patch(f"/api/v1/drivers/{me['id']}", headers=admin, json={"is_active": False})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_customer_with_orders_cannot_be_hard_deleted(client, two_drivers_one_order):
    admin = await login(client, "kitchenadmin", "Kitchen@123")
    async with SessionLocal() as db:
        order = await db.get(Order, uuid.UUID(two_drivers_one_order["order_id"]))
        customer_id = str(order.customer_id)
    res = await client.delete(f"/api/v1/customers/{customer_id}", headers=admin)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_generate_daily_is_idempotent(client):
    admin = await login(client, "kitchenadmin", "Kitchen@123")
    day = business_today().isoformat()
    first = (await client.post("/api/v1/orders/generate-daily", headers=admin, json={"date": day})).json()
    second = (await client.post("/api/v1/orders/generate-daily", headers=admin, json={"date": day})).json()
    assert first["generated_count"] > 0
    assert second["generated_count"] == 0
    assert second["existing_count"] == first["generated_count"]


def _ws_rejected(path: str) -> bool:
    with TestClient(app) as tc:
        try:
            with tc.websocket_connect(path) as ws:
                ws.receive_text()
        except WebSocketDisconnect as exc:
            return exc.code == 1008
    return False


@pytest.mark.asyncio
async def test_websockets_require_matching_token(two_drivers_one_order):
    owner_id = two_drivers_one_order["owner_id"]
    other_id = two_drivers_one_order["other_id"]
    owner_token = create_access_token(subject=owner_id, role="DRIVER")

    assert _ws_rejected(f"/api/v1/tracking/ws/driver/{owner_id}")
    assert _ws_rejected(f"/api/v1/tracking/ws/driver/{other_id}?token={owner_token}")
    assert _ws_rejected("/api/v1/tracking/ws/admin")
    assert _ws_rejected(f"/api/v1/tracking/ws/admin?token={owner_token}")
