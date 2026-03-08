"""
HostingSignal License Server — Input Validators
"""
import re
from typing import Optional
from pydantic import BaseModel, field_validator, EmailStr


# ── API Schemas ──────────────────────────────────────────────────────────────

class LicenseCreateRequest(BaseModel):
    customer_email: str
    customer_name: Optional[str] = None
    tier: str = "starter"
    bound_ip: Optional[str] = None
    bound_domain: Optional[str] = None
    max_activations: int = 1
    expires_days: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email address")
        return v.lower()

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v):
        valid_tiers = ["starter", "professional", "business", "enterprise"]
        if v.lower() not in valid_tiers:
            raise ValueError(f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")
        return v.lower()

    @field_validator("bound_ip")
    @classmethod
    def validate_ip(cls, v):
        if v is None:
            return v
        # Basic IPv4/IPv6 validation
        ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
        if not (re.match(ipv4_pattern, v) or re.match(ipv6_pattern, v)):
            raise ValueError("Invalid IP address format")
        return v


class LicenseActivateRequest(BaseModel):
    license_key: str
    server_ip: str
    hostname: Optional[str] = None
    cpu_id: Optional[str] = None
    disk_uuid: Optional[str] = None
    mac_address: Optional[str] = None
    machine_id: Optional[str] = None

    @field_validator("license_key")
    @classmethod
    def validate_license_key(cls, v):
        pattern = r"^HS-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid license key format. Expected: HS-XXXX-XXXX-XXXX-XXXX")
        return v.upper()


class LicenseValidateRequest(BaseModel):
    license_key: str
    fingerprint_hash: Optional[str] = None
    server_ip: Optional[str] = None


class LicenseRevokeRequest(BaseModel):
    license_key: str
    reason: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LicenseResponse(BaseModel):
    license_key: str
    customer_email: str
    customer_name: Optional[str] = None
    tier: str
    status: str
    bound_ip: Optional[str] = None
    bound_domain: Optional[str] = None
    max_activations: int
    issued_at: str
    expires_at: Optional[str] = None
    active_activations: int = 0


class ActivationResponse(BaseModel):
    license_key: str
    signed_token: str
    tier: str
    status: str
    message: str


class StatusResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None
