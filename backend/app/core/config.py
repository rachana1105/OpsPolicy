"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OpsPolicy"
    app_version: str = "1.0.0"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://opspolicy:opspolicy@postgres:5432/opspolicy"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    cors_origins: str = "http://localhost:5173"

    # Analytics provider: "mock" or "databricks"
    analytics_provider: str = "mock"
    databricks_host: str = ""
    databricks_token: str = ""

    # Retry delays (seconds) — configurable so demos run fast
    revocation_retry_delays: str = "60,300,900"
    sla_escalation_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def revocation_retry_delay_list(self) -> list[int]:
        return [int(x) for x in self.revocation_retry_delays.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
