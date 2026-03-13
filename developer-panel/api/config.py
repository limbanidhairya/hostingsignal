"""Developer Panel Configuration"""
from functools import lru_cache
import os


class Settings:
    # Application
    APP_NAME: str = os.getenv("HSDEV_APP_NAME", "HostingSignal Developer Panel")
    APP_VERSION: str = os.getenv("HSDEV_APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("HSDEV_DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HSDEV_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("HSDEV_PORT", "9000"))

    # Database
    DATABASE_URL: str = os.getenv("HSDEV_DATABASE_URL", "sqlite+aiosqlite:///./hostingsignal_dev.db")

    # Seeded admin (development bootstrap)
    DEFAULT_ADMIN_EMAIL: str = os.getenv("HSDEV_DEFAULT_ADMIN_EMAIL", "admin@hostingsignal.local")
    DEFAULT_ADMIN_USERNAME: str = os.getenv("HSDEV_DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("HSDEV_DEFAULT_ADMIN_PASSWORD", "Admin@123")

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



@lru_cache()
def get_settings() -> Settings:
    return Settings()
