"""Developer Panel — License Management API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import secrets

router = APIRouter(prefix="/api/licenses", tags=["Licenses"])

# In-memory store for dev; production uses PostgreSQL
_licenses: dict = {}


class CreateLicenseRequest(BaseModel):
    customer_email: str
    tier: str = "professional"  # starter | professional | business | enterprise
    max_domains: int = 20
    valid_days: int = 365
    ip_binding: Optional[str] = None
    domain_binding: Optional[str] = None


class LicenseResponse(BaseModel):
    key: str
    tier: str
    customer_email: str
    max_domains: int
    status: str
    created_at: str
    expires_at: str


@router.post("/create", response_model=LicenseResponse)
async def create_license(body: CreateLicenseRequest):
    """Create a new license key."""
    key = f"HS-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    now = datetime.now(timezone.utc)
    license_data = {
        "key": key,
        "tier": body.tier,
        "customer_email": body.customer_email,
        "max_domains": body.max_domains,
        "status": "inactive",
        "ip_binding": body.ip_binding,
        "domain_binding": body.domain_binding,
        "created_at": now.isoformat(),
        "expires_at": (now.replace(year=now.year + 1)).isoformat(),
        "activations": [],
    }
    _licenses[key] = license_data
    return LicenseResponse(**license_data)


@router.get("/list")
async def list_licenses(status: Optional[str] = None, tier: Optional[str] = None):
    """List all licenses with optional filtering."""
    results = list(_licenses.values())
    if status:
        results = [l for l in results if l["status"] == status]
    if tier:
        results = [l for l in results if l["tier"] == tier]
    return {"licenses": results, "total": len(results)}


@router.get("/{key}")
async def get_license(key: str):
    """Get license info by key."""
    if key not in _licenses:
        raise HTTPException(status_code=404, detail="License not found")
    return _licenses[key]


@router.post("/{key}/revoke")
async def revoke_license(key: str):
    """Revoke a license."""
    if key not in _licenses:
        raise HTTPException(status_code=404, detail="License not found")
    _licenses[key]["status"] = "revoked"
    return {"status": "success", "message": f"License {key} revoked"}


@router.get("/stats/overview")
async def license_stats():
    """Get license statistics."""
    total = len(_licenses)
    active = sum(1 for l in _licenses.values() if l["status"] == "active")
    inactive = sum(1 for l in _licenses.values() if l["status"] == "inactive")
    revoked = sum(1 for l in _licenses.values() if l["status"] == "revoked")
    return {"total": total, "active": active, "inactive": inactive, "revoked": revoked}
