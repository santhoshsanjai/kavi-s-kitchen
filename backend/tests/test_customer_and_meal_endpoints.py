import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection
from app.db.init_db import init_db


@pytest.mark.asyncio
async def test_customer_and_meal_management_flow():
    await connect_to_mongo()
    await init_db()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Login as Admin
            login_res = await ac.post(
                "/api/v1/auth/login",
                json={"identifier": "kitchenadmin", "password": "Kitchen@123"},
            )
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Test Get Customers
            customers_res = await ac.get("/api/v1/customers", headers=headers)
            assert customers_res.status_code == 200
            cust_data = customers_res.json()
            assert "items" in cust_data
            assert cust_data["total"] >= 1

            # 3. Test Create New Customer
            new_customer_payload = {
                "name": "Karthik Raja",
                "phone": "9840991122",
                "whatsapp_number": "9840991122",
                "customer_type": "INDIVIDUAL",
                "is_active": True,
                "address": {
                    "address_line": "12/A, 1st Street, Anna Nagar West",
                    "area": "Anna Nagar West",
                    "city": "Chennai",
                    "pincode": "600040",
                    "latitude": 13.0890,
                    "longitude": 80.2080
                },
                "meal_preference": {
                    "diet_type": "VEG",
                    "sessions": ["LUNCH", "DINNER"],
                    "spice_level": "NORMAL",
                    "rice_preference": "Ponni"
                },
                "notes": "Prefers delivery before 12:45 PM"
            }
            create_cust_res = await ac.post(
                "/api/v1/customers",
                json=new_customer_payload,
                headers=headers
            )
            assert create_cust_res.status_code == 201
            created_customer = create_cust_res.json()
            customer_id = created_customer["id"]
            assert created_customer["name"] == "Karthik Raja"
            assert created_customer["phone"] == "9840991122"

            # 4. Test Customer Toggle Status
            toggle_res = await ac.patch(
                f"/api/v1/customers/{customer_id}/status",
                json={"is_active": False},
                headers=headers
            )
            assert toggle_res.status_code == 200
            assert toggle_res.json()["is_active"] is False

            # 5. Test Get Meal Plans
            plans_res = await ac.get("/api/v1/meal-plans", headers=headers)
            assert plans_res.status_code == 200
            plans = plans_res.json()
            assert len(plans) >= 1
            assert any(p["name"] == "Veg Full Day" for p in plans)

            # 6. Test Enquiry Flow & Conversion
            new_enquiry_payload = {
                "customer_name": "Meena Kumari",
                "phone": "9884112299",
                "requested_meal": "Lunch Box",
                "number_of_persons": 1,
                "diet_type": "VEG",
                "subscription_type": "SUBSCRIPTION",
                "delivery_location": "Vadapalani, Chennai",
                "quoted_price": 2799.0,
                "notes": "Office lunch delivery"
            }
            create_enq_res = await ac.post(
                "/api/v1/enquiries",
                json=new_enquiry_payload,
                headers=headers
            )
            assert create_enq_res.status_code == 201
            enquiry = create_enq_res.json()
            enquiry_id = enquiry["id"]

            # Convert enquiry to customer
            convert_payload = {
                "address_line": "78 Arcot Road",
                "area": "Vadapalani",
                "city": "Chennai",
                "pincode": "600026",
                "latitude": 13.0500,
                "longitude": 80.2100
            }
            convert_res = await ac.post(
                f"/api/v1/enquiries/{enquiry_id}/convert",
                json=convert_payload,
                headers=headers
            )
            assert convert_res.status_code == 200
            conv_data = convert_res.json()
            assert conv_data["enquiry"]["status"] == "CONVERTED"
            assert conv_data["customer"]["name"] == "Meena Kumari"
            assert conv_data["customer"]["phone"] == "9884112299"
    finally:
        await close_mongo_connection()
