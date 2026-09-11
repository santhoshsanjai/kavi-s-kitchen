import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection
from app.db.init_db import init_db


@pytest.mark.asyncio
async def test_auth_flow():
    await connect_to_mongo()
    await init_db()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Test Health Check
            health_res = await ac.get("/health")
            assert health_res.status_code == 200
            assert health_res.json()["status"] == "ok"

            # Test Super Admin Login
            login_res = await ac.post(
                "/api/v1/auth/login",
                json={"identifier": "superadmin", "password": "Admin@123"},
            )
            assert login_res.status_code == 200
            data = login_res.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["user"]["username"] == "superadmin"
            assert data["role"] == "SUPER_ADMIN"
            assert "manage_users" in data["permissions"]

            token = data["access_token"]
            refresh_token = data["refresh_token"]

            # Test GET /me with Bearer token
            me_res = await ac.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_res.status_code == 200
            me_data = me_res.json()
            assert me_data["user"]["username"] == "superadmin"
            assert me_data["role"] == "SUPER_ADMIN"

            # Test POST /refresh
            refresh_res = await ac.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_res.status_code == 200
            assert "access_token" in refresh_res.json()

            # Test Driver Login
            driver_login = await ac.post(
                "/api/v1/auth/login",
                json={"identifier": "driver1", "password": "Driver@123"},
            )
            assert driver_login.status_code == 200
            driver_data = driver_login.json()
            assert driver_data["role"] == "DRIVER"
            assert "start_delivery" in driver_data["permissions"]

            # Test Invalid Login
            bad_login = await ac.post(
                "/api/v1/auth/login",
                json={"identifier": "superadmin", "password": "WrongPassword!"},
            )
            assert bad_login.status_code == 401
    finally:
        await close_mongo_connection()
