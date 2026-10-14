from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "Kavi's Kitchen"
    environment: str = "development"
    debug: bool = True

    # PostgreSQL (asyncpg driver), e.g. postgresql+asyncpg://kavis:kavis@localhost:5432/kavis_kitchen
    database_url: str = "postgresql+asyncpg://kavis:kavis@localhost:5432/kavis_kitchen"
    # Seeds demo users/plans/customers on startup. Only honoured in development.
    seed_demo_data: bool = True

    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    google_maps_api_key: Optional[str] = ""
    cors_origins: str = "http://localhost:5173"

    # Business timezone used for "today" and service dates
    business_timezone: str = "Asia/Kolkata"

    location_update_interval_seconds: int = 10
    location_min_distance_meters: int = 20

    free_delivery_radius_km: float = 3.0
    min_delivery_charge: float = 30.0
    standard_route_drop_payout: float = 15.0
    additional_nearby_drop_payout: float = 10.0


settings = Settings()
