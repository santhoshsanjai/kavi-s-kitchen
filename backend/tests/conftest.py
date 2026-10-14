"""
Tests run against a real PostgreSQL database (default: kavis_kitchen_test on localhost).
Override with TEST_DATABASE_URL. The schema is rebuilt from the Alembic migrations once per run,
and every test starts from empty tables plus the demo seed data.
"""
import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://kavis:kavis@localhost:5432/kavis_kitchen_test"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.init_db import seed_demo_data  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    config.attributes["database_url"] = os.environ["DATABASE_URL"]
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest_asyncio.fixture(autouse=True)
async def clean_database(request):
    # Pure unit tests (tests/unit) need no database
    if "unit" in request.node.path.parts:
        yield
        return
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with SessionLocal() as db:
        await db.execute(text(f"TRUNCATE {tables} CASCADE"))
        await db.commit()
        await seed_demo_data(db)
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def login(client: AsyncClient, identifier: str, password: str) -> dict:
    res = await client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
