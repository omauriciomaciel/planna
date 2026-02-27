from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Planna API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://planna:planna@localhost:5432/planna"

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_server: str = ""
    mail_port: int = 587
    mail_tls: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
