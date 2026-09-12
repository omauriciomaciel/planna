from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://planna:planna@localhost:5433/planna"
    cookie_secret: str = Field(min_length=32)
    frontend_url: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:3000/api"
    cors_origins: list[str] = ["http://localhost:3000"]
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    metrics_token: SecretStr | None = Field(default=None, min_length=32)
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
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-mini"
    openai_input_cost_per_million: Decimal = Decimal(0)
    openai_output_cost_per_million: Decimal = Decimal(0)

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_production_urls(self) -> "Settings":
        if self.app_env == "production" and (
            not self.frontend_url.startswith("https://")
            or not self.public_api_url.startswith("https://")
        ):
            raise ValueError("FRONTEND_URL e PUBLIC_API_URL devem usar HTTPS em produção")
        if self.app_env == "production" and not self.smtp_host:
            raise ValueError("SMTP_HOST deve ser configurado em produção")
        if self.app_env == "production" and self.metrics_token is None:
            raise ValueError("METRICS_TOKEN deve ser configurado em produção")
        if self.app_env == "production" and "*" in self.trusted_hosts:
            raise ValueError("TRUSTED_HOSTS não pode aceitar todos os hosts em produção")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
