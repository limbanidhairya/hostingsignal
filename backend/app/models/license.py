import enum
import secrets
import hashlib
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Enum, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.config import settings


class LicenseTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


# Tier configuration
TIER_CONFIG = {
    LicenseTier.FREE: {
        "max_domains": 1,
        "price_monthly": 0,
        "features": ["basic_panel"],
        "name": "Free",
    },
    LicenseTier.PRO: {
        "max_domains": 10,
        "price_monthly": 28,
        "features": ["basic_panel", "docker", "email", "daily_backups"],
        "name": "Pro",
    },
    LicenseTier.BUSINESS: {
        "max_domains": 50,
        "price_monthly": 48,
        "features": ["basic_panel", "docker", "email", "hourly_backups", "waf", "priority_support", "remote_backup"],
        "name": "Business",
    },
    LicenseTier.ENTERPRISE: {
        "max_domains": -1,  # Unlimited
        "price_monthly": 97,
        "features": ["basic_panel", "docker", "email", "hourly_backups", "waf", "priority_support", "remote_backup", "phone_support", "whmcs"],
        "name": "Enterprise",
    },
}


def generate_license_key() -> str:
    """Generate a cryptographically secure license key in format HS-XXXX-XXXX-XXXX-XXXX"""
    segments = []
    for _ in range(4):
        segment = secrets.token_hex(2).upper()
        segments.append(segment)
    return f"{settings.LICENSE_PREFIX}-{'-'.join(segments)}"


def generate_hardware_fingerprint(server_ip: str, hostname: str = "") -> str:
    """Generate a hardware fingerprint hash from server IP and hostname"""
    data = f"{server_ip}:{hostname}".encode()
    return hashlib.sha256(data).hexdigest()[:32]


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    license_key: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True, default=generate_license_key
    )

    # Customer
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # License details
    tier: Mapped[LicenseTier] = mapped_column(Enum(LicenseTier), default=LicenseTier.FREE, nullable=False)
    status: Mapped[LicenseStatus] = mapped_column(Enum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False)
    max_domains: Mapped[int] = mapped_column(Integer, default=1)

    # Server binding
    server_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    server_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hardware_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Activation
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Validity
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Transfer tracking
    transferred_from: Mapped[str | None] = mapped_column(String(45), nullable=True)
    transfer_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transfer_count: Mapped[int] = mapped_column(Integer, default=0)

    # Panel disabled flag (set on old server after transfer)
    panel_disabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    customer = relationship("User", back_populates="licenses", lazy="selectin")

    @property
    def is_valid(self) -> bool:
        if self.status != LicenseStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def tier_config(self) -> dict:
        return TIER_CONFIG.get(self.tier, TIER_CONFIG[LicenseTier.FREE])

    @property
    def monthly_revenue(self) -> int:
        if self.status == LicenseStatus.ACTIVE:
            return self.tier_config["price_monthly"]
        return 0

    def __repr__(self):
        return f"<License {self.license_key} ({self.tier.value}/{self.status.value})>"


class LicenseLog(Base):
    __tablename__ = "license_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # activated, deactivated, heartbeat, expired, etc.
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
