"""
HostingSignal License Server — Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "HostingSignal License Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8443

    # Database — PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://hostingsignal:secret@localhost:5432/hostingsignal_licenses"
    DATABASE_SYNC_URL: str = "postgresql://hostingsignal:secret@localhost:5432/hostingsignal_licenses"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-64"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_LICENSE_TOKEN_EXPIRE_DAYS: int = 365

    # API Keys
    MASTER_API_KEY: str = "hs-master-key-change-in-production"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # License
    LICENSE_PREFIX: str = "HS"
    MAX_ACTIVATIONS_PER_LICENSE: int = 1
    FINGERPRINT_TOLERANCE: int = 2  # How many fingerprint fields can differ on revalidation

    # Encryption
    ENCRYPTION_KEY: str = "change-me-32-byte-key-for-fernet!"  # Must be 32 url-safe base64-encoded bytes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
