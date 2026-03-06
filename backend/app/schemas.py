from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ===== Auth Schemas =====

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str
    company: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    company: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    totp_enabled: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ===== License Schemas =====

class LicenseCreate(BaseModel):
    customer_name: str
    customer_email: EmailStr
    tier: str = "free"
    server_ip: Optional[str] = None
    validity_months: int = 1
    notes: Optional[str] = None


class LicenseResponse(BaseModel):
    id: int
    license_key: str
    customer_name: str
    customer_email: str
    tier: str
    status: str
    max_domains: int
    server_ip: Optional[str] = None
    server_hostname: Optional[str] = None
    activated_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    notes: Optional[str] = None
    monthly_revenue: int = 0
    features: list[str] = []

    class Config:
        from_attributes = True


class LicenseValidate(BaseModel):
    license_key: str
    server_ip: str
    server_hostname: Optional[str] = ""


class LicenseValidationResponse(BaseModel):
    valid: bool
    license_key: str
    tier: str
    status: str
    features: list[str]
    max_domains: int
    expires_at: Optional[datetime] = None
    message: str


class LicenseActivate(BaseModel):
    license_key: str
    server_ip: str
    server_hostname: Optional[str] = ""


class LicenseHeartbeat(BaseModel):
    license_key: str
    server_ip: str
    server_hostname: Optional[str] = ""


class LicenseUpdate(BaseModel):
    tier: Optional[str] = None
    status: Optional[str] = None
    server_ip: Optional[str] = None
    notes: Optional[str] = None
    validity_months: Optional[int] = None


# ===== Stats Schemas =====

class DashboardStats(BaseModel):
    total_licenses: int
    active_licenses: int
    expired_licenses: int
    suspended_licenses: int
    monthly_revenue: int
    tier_breakdown: dict[str, int]
    total_users: int
    active_users: int


class LicenseStats(BaseModel):
    total: int
    active: int
    expired: int
    suspended: int
    revoked: int
    monthly_revenue: int
    tier_breakdown: dict[str, int]


# Forward ref
TokenResponse.model_rebuild()
