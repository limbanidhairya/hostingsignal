"""Developer Panel Configuration"""
from functools import lru_cache
import os


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # Application
    APP_NAME: str = os.getenv("HSDEV_APP_NAME", "HostingSignal Developer Panel")
    APP_VERSION: str = os.getenv("HSDEV_APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("HSDEV_DEBUG", "False").lower() == "true"
    PRODUCTION_MODE: bool = os.getenv("HSDEV_PRODUCTION_MODE", "False").lower() == "true"
    HOST: str = os.getenv("HSDEV_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("HSDEV_PORT", "9000"))

    # Database
    DATABASE_URL: str = os.getenv("HSDEV_DATABASE_URL", "sqlite+aiosqlite:///./hostingsignal_dev.db")

    # Seeded admin (development bootstrap)
    DEFAULT_ADMIN_EMAIL: str = os.getenv("HSDEV_DEFAULT_ADMIN_EMAIL", "admin@hostingsignal.local")
    DEFAULT_ADMIN_USERNAME: str = os.getenv("HSDEV_DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("HSDEV_DEFAULT_ADMIN_PASSWORD", "Admin@123")

    # Redis
    REDIS_URL: str = os.getenv("HSDEV_REDIS_URL", "redis://localhost:6379/2")

    # JWT
    JWT_SECRET: str = os.getenv("HSDEV_JWT_SECRET", "dev-panel-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # License Server
    LICENSE_SERVER_URL: str = os.getenv("HSDEV_LICENSE_SERVER_URL", "https://license.hostingsignal.com")
    LICENSE_API_KEY: str = os.getenv("HSDEV_LICENSE_API_KEY", "")
    LICENSE_VALIDATE_PATH: str = os.getenv("HSDEV_LICENSE_VALIDATE_PATH", "/license/validate")
    LICENSE_CACHE_PATH: str = os.getenv("HSDEV_LICENSE_CACHE_PATH", "/usr/local/hspanel/configs/license.cache")
    LICENSE_GRACE_HOURS: int = int(os.getenv("HSDEV_LICENSE_GRACE_HOURS", "72"))

    # Update Server
    UPDATE_SERVER_URL: str = "https://updates.hostingsignal.com"
    UPDATE_STORAGE_PATH: str = os.getenv("HSDEV_UPDATE_STORAGE_PATH", "/opt/hostingsignal-developer/updates")

    # Plugin Marketplace
    PLUGIN_STORAGE_PATH: str = os.getenv("HSDEV_PLUGIN_STORAGE_PATH", "/opt/hostingsignal-developer/plugins")
    PLUGIN_REVIEW_WEBHOOK: str = ""

    # Analytics
    ANALYTICS_RETENTION_DAYS: int = 90

    # Cluster
    CLUSTER_HEARTBEAT_INTERVAL: int = 30
    CLUSTER_TIMEOUT: int = 90

    # Monitoring
    MONITOR_INTERVAL: int = 15
    LOCAL_MONITOR_ENABLED: bool = _as_bool(os.getenv("HSDEV_LOCAL_MONITOR_ENABLED", "true"), True)

    # Local node bootstrap
    AUTO_REGISTER_LOCAL_SERVER: bool = _as_bool(os.getenv("HSDEV_AUTO_REGISTER_LOCAL_SERVER", "true"), True)
    LOCAL_SERVER_HOSTNAME: str = os.getenv("HSDEV_LOCAL_SERVER_HOSTNAME", "backend")
    LOCAL_SERVER_ADDRESS: str = os.getenv("HSDEV_LOCAL_SERVER_ADDRESS", "backend")
    LOCAL_SERVER_PORT: int = int(os.getenv("HSDEV_LOCAL_SERVER_PORT", "2083"))
    LOCAL_SERVER_REGION: str = os.getenv("HSDEV_LOCAL_SERVER_REGION", "Local Installation")
    LOCAL_SERVER_OS_INFO: str = os.getenv("HSDEV_LOCAL_SERVER_OS_INFO", "HostingSignal Panel Node")
    LOCAL_SERVER_LICENSE_KEY: str = os.getenv("HSDEV_LOCAL_SERVER_LICENSE_KEY", "")

    # WHMCS Integration
    WHMCS_SHARED_SECRET: str = os.getenv("HSDEV_WHMCS_SHARED_SECRET", "change-this-whmcs-secret")
    WHMCS_ALLOWED_IPS: str = os.getenv("HSDEV_WHMCS_ALLOWED_IPS", "")
    WHMCS_HMAC_SECRET: str = os.getenv("HSDEV_WHMCS_HMAC_SECRET", "")
    WHMCS_HMAC_MAX_SKEW_SECONDS: int = int(os.getenv("HSDEV_WHMCS_HMAC_MAX_SKEW_SECONDS", "300"))
    WHMCS_NONCE_TTL_SECONDS: int = int(os.getenv("HSDEV_WHMCS_NONCE_TTL_SECONDS", "600"))



@lru_cache()
def get_settings() -> Settings:
    return Settings()
