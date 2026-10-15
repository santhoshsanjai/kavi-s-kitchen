"""Phase 2 admin APIs end to end on PostgreSQL."""
import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.time import utcnow
from app.domain.task_states import TaskStatus
from app.models.user import User
from app.services import task_service, trip_service
from tests.conftest import login

pytestmark = pytest.mark.asyncio

API = "/api/v1/admin"
MONTH = "2030-01"
DAY = "2030-01-15"   # a Tuesday


@pytest_asyncio.fixture
async def admin(client):
    return await login(client, "kitchenadmin", "Kitchen@123")


async def _setup(client, admin):
    """Settings with real rates from Jan 2030, a plan, a customer with a map location, an active subscription."""
    current = (await client.get(f"{API}/settings", headers=admin)).json()
    s = current["settings"]
    s["delivery_fees"]["customer_rate_per_km"] = "10"
    s["payout"].update(per_km_rate="4", per_drop_amount="15", fixed_allowance="50")
    s["kitchen"].update(latitude=13.05, longitude=80.24, address="Kitchen")
    res = await client.post(f"{API}/settings/versions", headers=admin,
                            json={"effective_from": "2030-01-01", "settings": s, "reason": "Owner rates"})
    assert res.status_code == 201, res.text

    plan = await client.post("/api/v1/meal-plans", headers=admin, json={
        "name": "API Full Day", "diet_type": "VEG", "meal_sessions": ["BREAKFAST", "LUNCH", "DINNER"],
        "price": 5500, "billing_cycle": "MONTHLY", "service_days": 26})
    assert plan.status_code == 201, plan.text
    cust = await client.post("/api/v1/customers", headers=admin, json={
        "name": "Chitra", "phone": "9000000301", "customer_type": "INDIVIDUAL",
        "address": {"address_line": "1 Beach Rd", "area": "Adyar", "city": "Chennai", "pincode": "600020",
                    "latitude": 13.0, "longitude": 80.25},
        "meal_preference": {"diet_type": "VEG", "sessions": ["LUNCH"]}})
    assert cust.status_code == 201, cust.text
    sub = await client.post(f"{API}/subscriptions", headers=admin, json={
        "customer_id": cust.json()["id"], "plan_id": plan.json()["id"], "service_month": MONTH})
    assert sub.status_code == 201, sub.text
    return plan.json(), cust.json(), sub.json()


async def test_admin_routes_need_an_admin(client):
    assert (await client.get(f"{API}/dashboard")).status_code == 401
    driver = await login(client, "driver1", "Driver@123")
    for path in ["/dashboard", "/settings", "/meal-grid?month=2030-01", "/ledger/balances", "/reports/ledger"]:
        assert (await client.get(API + path, headers=driver)).status_code == 403, path


async def test_settings_versions_and_calendar(client, admin):
    res = await client.get(f"{API}/settings", headers=admin)
    assert res.json()["uses_defaults"] is True
    body = {"effective_from": "2030-01-01", "settings": res.json()["settings"]}
    assert (await client.post(f"{API}/settings/versions", headers=admin, json={**body, "reason": " "})).status_code == 422
    assert (await client.post(f"{API}/settings/versions", headers=admin,
                              json={**body, "effective_from": "2001-01-01", "reason": "x"})).status_code == 422
    assert (await client.post(f"{API}/settings/versions", headers=admin, json={**body, "reason": "x"})).status_code == 201
    assert (await client.post(f"{API}/settings/versions", headers=admin, json={**body, "reason": "x"})).status_code == 409

    cal = (await client.get(f"{API}/calendar?month={MONTH}", headers=admin)).json()
    assert len(cal["service_dates"]) == 27  # Mon-Sat in Jan 2030
    res = await client.put(f"{API}/calendar/exceptions", headers=admin,
                           json={"service_date": "2030-01-26", "is_open": False, "reason": "Republic Day"})
    assert res.status_code == 200, res.text
    cal = (await client.get(f"{API}/calendar?month={MONTH}", headers=admin)).json()
    assert "2030-01-26" not in cal["service_dates"] and len(cal["service_dates"]) == 26
    # Opening a Sunday is off until the owner enables it (open decision)
    res = await client.put(f"{API}/calendar/exceptions", headers=admin,
                           json={"service_date": "2030-01-27", "is_open": True, "reason": "Special"})
    assert res.status_code == 422


async def test_plan_rate_versions(client, admin):
    plan, _, _ = await _setup(client, admin)
    res = await client.post(f"{API}/plans/{plan['id']}/rates", headers=admin, json={
        "effective_from": "2030-02-01", "monthly_amount": 6000, "included_meals": ["LUNCH", "BREAKFAST"]})
    assert res.status_code == 422  # reason required
    res = await client.post(f"{API}/plans/{plan['id']}/rates", headers=admin, json={
        "effective_from": "2030-02-01", "monthly_amount": 6000, "included_meals": ["LUNCH", "BREAKFAST"],
        "reason": "Price revision"})
    assert res.status_code == 201, res.text
    assert res.json()["included_meals"] == ["BREAKFAST", "LUNCH"]
    rates = (await client.get(f"{API}/plans/{plan['id']}/rates", headers=admin)).json()["rates"]
    assert [r["effective_from"] for r in rates] == ["2030-02-01", "2030-01-01"]
    pv = (await client.post(f"{API}/subscriptions/preview", headers=admin,
                            json={"plan_id": plan["id"], "service_month": "2030-02"})).json()
    assert pv["plan_amount"] == 6000 and pv["included_meals"] == ["BREAKFAST", "LUNCH"]


async def test_subscription_grid_skip_and_restore(client, admin):
    plan, cust, sub = await _setup(client, admin)
    assert sub["total_slots"] == 81 and sub["per_meal_value"] == 67.9
    dup = await client.post(f"{API}/subscriptions", headers=admin, json={
        "customer_id": cust["id"], "plan_id": plan["id"], "service_month": MONTH})
    assert dup.status_code == 409

    grid = (await client.get(f"{API}/meal-grid?month={MONTH}", headers=admin)).json()
    assert len(grid["dates"]) == 27 and grid["rows"][0]["customer_name"] == "Chitra"
    assert grid["rows"][0]["cells"][DAY]["LUNCH"]["status"] == "SCHEDULED"

    targets = {"targets": [{"service_date": DAY}, {"service_date": "2030-01-16", "meal_window": "LUNCH"}]}
    pv = (await client.post(f"{API}/subscriptions/{sub['id']}/skip-preview", headers=admin, json=targets)).json()
    assert pv["on_time"] == 4 and pv["late"] == 0 and pv["credit"] == 271.6
    assert (await client.post(f"{API}/subscriptions/{sub['id']}/skip", headers=admin, json=targets)).status_code == 422
    res = await client.post(f"{API}/subscriptions/{sub['id']}/skip", headers=admin,
                            json={**targets, "reason": "Travelling"})
    assert res.status_code == 200, res.text
    assert res.json() == {"meals": 4, "credit_eligible": 4, "late": 0, "credit_posted": 271.6}
    # Skipping again is a no-op
    again = (await client.post(f"{API}/subscriptions/{sub['id']}/skip", headers=admin,
                               json={**targets, "reason": "Travelling"})).json()
    assert again["meals"] == 0 and again["credit_posted"] == 0

    ledger = (await client.get(f"{API}/customers/{cust['id']}/ledger", headers=admin)).json()
    assert ledger["balance"] == 5500 - 271.6
    assert [e["entry_type"] for e in ledger["entries"]] == ["SUBSCRIPTION_CHARGE", "SKIP_CREDIT"]

    res = await client.post(f"{API}/subscriptions/{sub['id']}/restore", headers=admin,
                            json={"targets": [{"service_date": "2030-01-16", "meal_window": "LUNCH"}],
                                  "reason": "Plans changed"})
    assert res.json()["credit_posted"] == -67.9
    ledger = (await client.get(f"{API}/customers/{cust['id']}/ledger", headers=admin)).json()
    assert ledger["balance"] == pytest.approx(5500 - 203.7)
    detail = (await client.get(f"{API}/subscriptions/{sub['id']}", headers=admin)).json()
    assert sum(s["status"] == "SKIPPED" for s in detail["slots"]) == 3


async def test_menu_publish_and_change_notice(client, admin):
    _, cust, _ = await _setup(client, admin)
    item = await client.post(f"{API}/food-items", headers=admin, json={"name": "Idli", "diet_label": "VEG"})
    assert item.status_code == 201
    assert (await client.post(f"{API}/food-items", headers=admin,
                              json={"name": "Idli", "diet_label": "VEG"})).status_code == 409
    item2 = (await client.post(f"{API}/food-items", headers=admin, json={"name": "Pongal", "diet_label": "VEG"})).json()

    week = "2030-01-14"
    assert (await client.post(f"{API}/menus/{week}/publish", headers=admin)).status_code == 422  # empty
    entries = {"entries": [{"service_date": DAY, "meal_window": "BREAKFAST", "food_item_id": item.json()["id"]}]}
    assert (await client.put(f"{API}/menus/2030-01-15/entries", headers=admin, json=entries)).status_code == 422
    assert (await client.put(f"{API}/menus/{week}/entries", headers=admin, json=entries)).status_code == 200
    first = (await client.post(f"{API}/menus/{week}/publish", headers=admin)).json()
    assert first["published_version"] == 1 and first["notified_customers"] == 0

    driver = await login(client, "driver1", "Driver@123")
    public = (await client.get(f"/api/v1/menus/{DAY}", headers=driver)).json()
    assert public["published"] and public["entries"][0]["name"] == "Idli"

    entries["entries"].append({"service_date": DAY, "meal_window": "BREAKFAST", "food_item_id": item2["id"]})
    draft = (await client.put(f"{API}/menus/{week}/entries", headers=admin, json=entries)).json()
    assert draft["has_unpublished_changes"] is True
    second = (await client.post(f"{API}/menus/{week}/publish", headers=admin)).json()
    assert second["published_version"] == 2 and second["notified_customers"] == 1
    inbox = (await client.get(f"{API}/customers/{cust['id']}/inbox", headers=admin)).json()
    assert inbox[0]["kind"] == "MENU_CHANGED"


async def test_one_time_order_confirm_and_reject(client, admin):
    _, cust, _ = await _setup(client, admin)
    body = {"customer_id": cust["id"], "idempotency_key": "req-1",
            "lines": [{"service_date": DAY, "meal_window": "DINNER", "quantity": 2, "description": "Extra chapati"}]}
    order = (await client.post(f"{API}/one-time-orders", headers=admin, json=body)).json()
    assert order["status"] == "REQUEST_PENDING" and order["source"] == "ADMIN"
    assert (await client.post(f"{API}/one-time-orders", headers=admin, json=body)).json()["id"] == order["id"]

    line_id = order["lines"][0]["id"]
    assert (await client.post(f"{API}/one-time-orders/{order['id']}/confirm", headers=admin,
                              json={"unit_prices": {}})).status_code == 422
    res = await client.post(f"{API}/one-time-orders/{order['id']}/confirm", headers=admin,
                            json={"unit_prices": {line_id: 60}, "discount": 20})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "CONFIRMED" and res.json()["total"] == 100
    pending = (await client.get(f"{API}/one-time-orders?status=REQUEST_PENDING", headers=admin)).json()
    assert pending == []

    other = (await client.post(f"{API}/one-time-orders", headers=admin, json={**body, "idempotency_key": "req-2"})).json()
    assert (await client.post(f"{API}/one-time-orders/{other['id']}/reject", headers=admin, json={})).status_code == 422
    rejected = (await client.post(f"{API}/one-time-orders/{other['id']}/reject", headers=admin,
                                  json={"reason": "Kitchen closed"})).json()
    assert rejected["status"] == "REJECTED"
    ledger = (await client.get(f"{API}/customers/{cust['id']}/ledger", headers=admin)).json()
    assert ledger["balance"] == 5500 + 100


async def test_dispatch_trip_manual_distance_and_earnings(client, admin):
    _, cust, _ = await _setup(client, admin)
    gen = (await client.post(f"{API}/dispatch/generate?service_date={DAY}", headers=admin)).json()
    assert gen["created"] == 3
    assert (await client.post(f"{API}/dispatch/generate?service_date={DAY}", headers=admin)).json()["created"] == 0

    tasks = (await client.get(f"{API}/dispatch/tasks?service_date={DAY}&meal_window=LUNCH", headers=admin)).json()
    assert len(tasks) == 1 and tasks[0]["customer_name"] == "Chitra"
    task_id = tasks[0]["id"]
    async with SessionLocal() as db:
        driver = (await db.execute(select(User).where(User.username == "driver1"))).scalars().one()
    res = await client.post(f"{API}/dispatch/tasks/{task_id}/assign", headers=admin, json={"driver_id": str(driver.id)})
    assert res.status_code == 200 and res.json()["status"] == "ASSIGNED" and res.json()["offer_expires_at"]
    assert (await client.post(f"{API}/dispatch/tasks/{task_id}/assign", headers=admin,
                              json={"driver_id": str(driver.id)})).status_code == 409
    seq = await client.put(f"{API}/dispatch/trips/sequence", headers=admin, json={
        "driver_id": str(driver.id), "service_date": DAY, "meal_window": "LUNCH", "task_ids": [task_id]})
    assert seq.status_code == 200, seq.text
    trip_id = seq.json()["id"]

    # Driver side (driver app arrives in Phase 3): accept, start, deliver, end without Maps
    async with SessionLocal() as db:
        now = utcnow()
        await task_service.accept(db, task_id=uuid.UUID(task_id), driver_id=driver.id, now=now)
        await trip_service.start_trip(db, trip_id=uuid.UUID(trip_id), driver_id=driver.id, now=now)
        await trip_service.record_outcome(db, task_id=uuid.UUID(task_id), driver_id=driver.id,
                                          outcome=TaskStatus.DELIVERED, now=now)
        await trip_service.end_trip(db, trip_id=uuid.UUID(trip_id), driver_id=driver.id, now=now, provider=None)
        await db.commit()

    trips = (await client.get(f"{API}/trips?service_date={DAY}", headers=admin)).json()
    assert trips[0]["distance_status"] == "NEEDS_MANUAL_ENTRY" and trips[0]["visited_stops"] == 1
    dash = (await client.get(f"{API}/dashboard?service_date={DAY}", headers=admin)).json()
    assert dash["trips_needing_distance"] == 1 and dash["tasks_by_status"]["DELIVERED"] == 1
    alerts = (await client.get(f"{API}/alerts", headers=admin)).json()
    assert any(a["kind"] == "TRIP_DISTANCE_NEEDED" for a in alerts)

    bad = await client.post(f"{API}/trips/{trip_id}/manual-distance", headers=admin,
                            json={"stop_legs_km": [3, 1], "return_leg_km": 3, "reason": "Odometer"})
    assert bad.status_code == 422
    res = await client.post(f"{API}/trips/{trip_id}/manual-distance", headers=admin,
                            json={"stop_legs_km": [6.5], "return_leg_km": 6, "reason": "Odometer reading"})
    assert res.status_code == 200, res.text
    assert res.json()["payable_km"] == 6.5 and res.json()["legs"][0]["source"] == "MANUAL"
    ledger = (await client.get(f"{API}/customers/{cust['id']}/ledger", headers=admin)).json()
    assert ledger["entries"][-1]["entry_type"] == "DELIVERY_FEE" and ledger["entries"][-1]["amount"] == 65

    day = {"driver_id": str(driver.id), "service_date": DAY}
    calc = (await client.post(f"{API}/earnings/calculate", headers=admin, json=day)).json()
    assert calc["status"] == "PROPOSED" and calc["total_amount"] == 6.5 * 4 + 15 + 50
    final = (await client.post(f"{API}/earnings/finalize", headers=admin, json=day)).json()
    assert final["status"] == "FINALIZED"
    assert (await client.post(f"{API}/trips/{trip_id}/manual-distance", headers=admin,
                              json={"stop_legs_km": [7], "return_leg_km": 6, "reason": "x"})).status_code == 409
    adj = await client.post(f"{API}/earnings/adjustments", headers=admin, json={**day, "amount": 20, "reason": "Rain"})
    assert adj.status_code == 201 and adj.json()["total_amount"] == 91 + 20
    listing = (await client.get(f"{API}/earnings?service_date={DAY}", headers=admin)).json()
    assert listing["summaries"][0]["driver_name"] == driver.full_name

    audit = (await client.get(f"{API}/audit?entity_type=delivery_trip", headers=admin)).json()
    assert {"trip.manual_distance", "trip.stop_sequence_set"} <= {a["action"] for a in audit}
    alert_id = next(a["id"] for a in alerts if a["kind"] == "TRIP_DISTANCE_NEEDED")
    assert (await client.post(f"{API}/alerts/{alert_id}/resolve", headers=admin)).json()["resolved_at"]


async def test_payments_adjustments_and_balances(client, admin):
    _, cust, sub = await _setup(client, admin)
    body = {"customer_id": cust["id"], "method": "UPI", "amount": 3000, "reference": "UPI-77",
            "idempotency_key": "pay-0001", "allocations": [{"amount": 3000, "subscription_id": sub["id"]}]}
    first = await client.post(f"{API}/payments", headers=admin, json=body)
    assert first.status_code == 201 and first.json()["balance"] == 2500
    again = await client.post(f"{API}/payments", headers=admin, json=body)
    assert again.json()["id"] == first.json()["id"] and again.json()["balance"] == 2500
    over = {**body, "idempotency_key": "pay-0002", "amount": 100}
    assert (await client.post(f"{API}/payments", headers=admin, json=over)).status_code == 422

    assert (await client.post(f"{API}/customers/{cust['id']}/adjustments", headers=admin,
                              json={"amount": -100})).status_code == 422
    adj = await client.post(f"{API}/customers/{cust['id']}/adjustments", headers=admin,
                            json={"amount": -100, "reason": "Goodwill for late skip"})
    assert adj.json()["balance"] == 2400
    balances = (await client.get(f"{API}/ledger/balances", headers=admin)).json()
    assert balances == [{"customer_id": cust["id"], "customer_name": "Chitra", "phone": "9000000301", "balance": 2400}]
    payments = (await client.get(f"{API}/payments?customer_id={cust['id']}", headers=admin)).json()
    assert payments[0]["allocations"][0]["amount"] == 3000


async def test_reports_export_in_three_formats(client, admin):
    await _setup(client, admin)
    today = date.today().isoformat()
    for fmt, media, magic in [("csv", "text/csv", b"\xef\xbb\xbfCustomer"),
                              ("xlsx", "spreadsheetml", b"PK"), ("pdf", "application/pdf", b"%PDF")]:
        res = await client.get(f"{API}/reports/balances?format={fmt}&end={today}", headers=admin)
        assert res.status_code == 200 and media in res.headers["content-type"], fmt
        assert res.content.startswith(magic), fmt
        assert "attachment" in res.headers["content-disposition"]
    preview = (await client.get(f"{API}/reports/balances/preview?end={today}", headers=admin)).json()
    assert preview["rows"] == [["Chitra", "9000000301", 5500.0]]
    assert (await client.get(f"{API}/reports/ledger?start=2030-02-01&end=2030-01-01", headers=admin)).status_code == 422


async def test_create_driver(client, admin):
    body = {"full_name": "New Rider", "username": "rider9", "phone": "9000000999", "password": "Rider@1234"}
    res = await client.post(f"{API}/drivers", headers=admin, json=body)
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "DRIVER" and res.json()["driver_code"].startswith("D")
    assert (await client.post(f"{API}/drivers", headers=admin, json=body)).status_code == 409
    await login(client, "rider9", "Rider@1234")
