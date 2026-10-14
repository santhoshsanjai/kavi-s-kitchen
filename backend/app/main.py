from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import check_database, engine
from app.api.v1.api import api_router
from app.db.init_db import init_db
from app.services.jobs import assignment_expiry_loop
from contextlib import asynccontextmanager, suppress
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic (`alembic upgrade head`), not created here.
    await init_db()
    expiry_job = None
    if settings.environment != "test":
        expiry_job = asyncio.create_task(assignment_expiry_loop())
    yield
    if expiry_job:
        expiry_job.cancel()
        with suppress(asyncio.CancelledError):
            await expiry_job
    await engine.dispose()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan
)

# Configure CORS
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check(response: Response):
    if await check_database():
        return {"status": "ok", "database": "connected"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "database": "unavailable"}

# Include routers
app.include_router(api_router, prefix="/api/v1")
