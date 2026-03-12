"""Developer Panel — License Management API (service-backed)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.license_sync import license_sync

router = APIRouter(prefix="/api/licenses", tags=["Licenses"])


class CreateLicenseRequest(BaseModel):
    customer_email: str
    tier: str = "professional"
    max_domains: int = 20
    valid_days: int = 365
    ip_binding: Optional[str] = None
    domain_binding: Optional[str] = None


def _fallback_domain(email: str) -> str:
    parts = email.split("@", 1)
    return parts[1] if len(parts) == 2 else "example.com"


@router.post("/create")
async def create_license(body: CreateLicenseRequest) -> dict:
    try:
        payload = await license_sync.create_license(
            plan=body.tier,
            domain=body.domain_binding or _fallback_domain(body.customer_email),
            max_domains=body.max_domains,
            expiry_days=body.valid_days,
            features={
                "ip_binding": body.ip_binding,
                "customer_email": body.customer_email,
            },
        )
        return {"success": True, "data": payload}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"License service error: {exc}") from exc


@router.get("/list")
async def list_licenses(
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
) -> dict:
    try:
        payload = await license_sync.list_licenses(page=page, per_page=per_page, status=status)
        return {"success": True, "data": payload}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"License service error: {exc}") from exc


@router.get("/{key}")
async def get_license(key: str) -> dict:
    try:
        payload = await license_sync.get_license_info(key)
        return {"success": True, "data": payload}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"License not found or service error: {exc}") from exc


@router.post("/{key}/revoke")
async def revoke_license(key: str, reason: str = "Revoked from developer panel") -> dict:
    try:
        payload = await license_sync.revoke_license(key, reason=reason)
        return {"success": True, "data": payload}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"License service error: {exc}") from exc


@router.get("/stats/overview")
async def license_stats() -> dict:
    try:
        payload = await license_sync.get_license_stats()
        return {"success": True, "data": payload, "generated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"License service error: {exc}") from exc
