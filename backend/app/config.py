from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://planna:planna@localhost:5433/planna"
    cookie_secret: str = Field(min_length=32)
    frontend_url: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:3000/api"
    cors_origins: list[str] = ["http://localhost:3000"]
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "acesso@planna.local"
    smtp_use_tls: bool = True
    pluggy_client_id: str | None = None
    pluggy_client_secret: str | None = None
    pluggy_webhook_url: str | None = None
    pluggy_webhook_secret: str | None = Field(default=None, min_length=32)

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
