from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables."""

    database_url: str
    auth_secret_key: str
    cors_origins: str = "http://localhost:5173"
    access_token_expire_minutes: int = 30
    lockout_max_attempts: int = 5
    lockout_duration_minutes: int = 15
    app_environment: Literal["development", "test", "production"] = "development"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict"] = "lax"
    auth_cookie_name: str = "acxiomcrm_access"
    csrf_cookie_name: str = "acxiomcrm_csrf"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def require_secure_production_cookies(self) -> "Settings":
        if len(self.auth_secret_key) < 32:
            raise ValueError("AUTH_SECRET_KEY must be at least 32 characters long.")
        if self.app_environment == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
