from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # App
    APP_NAME: str = "HostingSignal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./hostingsignal.db"

    # JWT Auth
    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # License
    LICENSE_PREFIX: str = "HS"
    LICENSE_VALIDATION_INTERVAL_HOURS: int = 24
    LICENSE_GRACE_PERIOD_DAYS: int = 7

    # CyberPanel Integration
    CYBERPANEL_URL: Optional[str] = None
    CYBERPANEL_API_KEY: Optional[str] = None
    CYBERPANEL_ADMIN_USER: str = "admin"
    CYBERPANEL_ADMIN_PASS: Optional[str] = None

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # SMTP (for license emails)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: str = "noreply@hostingsignal.com"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
