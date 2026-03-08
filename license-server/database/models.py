"""
HostingSignal License Server — Database Models
"""
import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    Enum, ForeignKey, JSON, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.connection import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class LicenseTier(str, enum.Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ActivationStatus(str, enum.Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    MIGRATED = "migrated"


# ── Tier Configuration ───────────────────────────────────────────────────────

TIER_CONFIG = {
    LicenseTier.STARTER: {
        "name": "Starter",
        "price_monthly": 0.00,
        "max_domains": 2,
        "max_databases": 2,
        "max_email_accounts": 5,
        "features": ["ssl", "dns", "basic_monitoring"],
    },
    LicenseTier.PROFESSIONAL: {
        "name": "Professional",
        "price_monthly": 9.99,
        "max_domains": 20,
        "max_databases": 20,
        "max_email_accounts": 50,
        "features": ["ssl", "dns", "monitoring", "backups", "firewall"],
    },
    LicenseTier.BUSINESS: {
        "name": "Business",
        "price_monthly": 24.99,
        "max_domains": 100,
        "max_databases": 100,
        "max_email_accounts": 500,
        "features": ["ssl", "dns", "monitoring", "backups", "firewall", "docker", "email_hosting"],
    },
    LicenseTier.ENTERPRISE: {
        "name": "Enterprise",
        "price_monthly": 49.99,
        "max_domains": -1,  # unlimited
        "max_databases": -1,
        "max_email_accounts": -1,
        "features": ["ssl", "dns", "monitoring", "backups", "firewall", "docker", "email_hosting", "clustering", "priority_support"],
    },
}


# ── Models ───────────────────────────────────────────────────────────────────

class AdminUser(Base):
    """License server admin users."""
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    licenses_created = relationship("License", back_populates="created_by_user", lazy="selectin")


class License(Base):
    """License keys issued to customers."""
    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_key = Column(String(30), unique=True, nullable=False, index=True)  # HS-XXXX-XXXX-XXXX-XXXX
    customer_email = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    tier = Column(Enum(LicenseTier), nullable=False, default=LicenseTier.STARTER)
    status = Column(Enum(LicenseStatus), nullable=False, default=LicenseStatus.ACTIVE)

    # Binding
    bound_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    bound_domain = Column(String(255), nullable=True)
    max_activations = Column(Integer, default=1)

    # Dates
    issued_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    # Foreign keys
    created_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)

    # Relationships
    created_by_user = relationship("AdminUser", back_populates="licenses_created")
    activations = relationship("Activation", back_populates="license", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_licenses_status_tier", "status", "tier"),
    )


class Activation(Base):
    """Records of license activations on specific servers."""
    __tablename__ = "activations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_id = Column(UUID(as_uuid=True), ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False)

    # Server fingerprint
    server_ip = Column(String(45), nullable=False)
    hostname = Column(String(255), nullable=True)
    cpu_id = Column(String(255), nullable=True)
    disk_uuid = Column(String(255), nullable=True)
    mac_address = Column(String(17), nullable=True)
    machine_id = Column(String(255), nullable=True)
    fingerprint_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of combined fingerprint

    # Token
    signed_token = Column(Text, nullable=True)

    # Status
    status = Column(Enum(ActivationStatus), nullable=False, default=ActivationStatus.ACTIVE)
    activated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_check_in = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    license = relationship("License", back_populates="activations")

    __table_args__ = (
        UniqueConstraint("license_id", "fingerprint_hash", name="uq_license_fingerprint"),
        Index("ix_activations_license_status", "license_id", "status"),
    )


class AuditLog(Base):
    """Audit trail for license operations."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(50), nullable=False, index=True)  # create, activate, validate, revoke, etc.
    license_key = Column(String(30), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_audit_created", "created_at"),
    )
