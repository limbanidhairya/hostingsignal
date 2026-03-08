"""Developer Panel Configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "HostingSignal Developer Panel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 9000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hsdev:hsdev@localhost:5432/hostingsignal_dev"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/2"

    # JWT
    JWT_SECRET: str = "dev-panel-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # License Server
    LICENSE_SERVER_URL: str = "https://license.hostingsignal.com"
    LICENSE_API_KEY: str = ""

    # Update Server
    UPDATE_SERVER_URL: str = "https://updates.hostingsignal.com"
    UPDATE_STORAGE_PATH: str = "/opt/hostingsignal-developer/updates"

    # Plugin Marketplace
    PLUGIN_STORAGE_PATH: str = "/opt/hostingsignal-developer/plugins"
    PLUGIN_REVIEW_WEBHOOK: str = ""

    # Analytics
    ANALYTICS_RETENTION_DAYS: int = 90

    # Cluster
    CLUSTER_HEARTBEAT_INTERVAL: int = 30
    CLUSTER_TIMEOUT: int = 90

    # Monitoring
    MONITOR_INTERVAL: int = 15

    class Config:
        env_file = ".env"
        env_prefix = "HSDEV_"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
