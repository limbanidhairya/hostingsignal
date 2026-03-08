"""
HostingSignal License Server — License API Routes
POST /license/create, /license/activate, /license/validate, /license/revoke
GET  /license/info, /license/status
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from middleware.auth_middleware import get_current_user, require_superadmin
from middleware.rate_limiter import limiter
from services.license_service import (
    create_license, activate_license, validate_license,
    revoke_license, get_license_info, list_licenses,
)
from utils.validators import (
    LicenseCreateRequest, LicenseActivateRequest,
    LicenseValidateRequest, LicenseRevokeRequest,
)

router = APIRouter(prefix="/license", tags=["License Management"])


@router.post("/create")
@limiter.limit("10/minute")
async def api_create_license(
    request: Request,
    body: LicenseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_superadmin),
):
    """Create a new license key. Requires superadmin access."""
    from uuid import UUID
    created_by = UUID(current_user["id"]) if current_user.get("id") else None

    license_obj = await create_license(
        db=db,
        customer_email=body.customer_email,
        tier=body.tier,
        customer_name=body.customer_name,
        bound_ip=body.bound_ip,
        bound_domain=body.bound_domain,
        max_activations=body.max_activations,
        expires_days=body.expires_days,
        notes=body.notes,
        created_by=created_by,
    )
    return {
        "status": "success",
        "license_key": license_obj.license_key,
        "tier": license_obj.tier.value,
        "customer_email": license_obj.customer_email,
        "message": "License created successfully.",
    }


@router.post("/activate")
@limiter.limit("5/minute")
async def api_activate_license(
    request: Request,
    body: LicenseActivateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a license on a server. 
    Called by panel installations — no auth required, rate limited.
    """
    result = await activate_license(
        db=db,
        license_key=body.license_key,
        server_ip=body.server_ip,
        hostname=body.hostname,
        cpu_id=body.cpu_id,
        disk_uuid=body.disk_uuid,
        mac_address=body.mac_address,
        machine_id=body.machine_id,
    )

    if "error" in result:
        raise HTTPException(status_code=result.get("status", 400), detail=result["error"])

    return result


@router.post("/validate")
@limiter.limit("30/minute")
async def api_validate_license(
    request: Request,
    body: LicenseValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a license key. Called periodically by panel installations.
    No auth required — rate limited.
    """
    result = await validate_license(
        db=db,
        license_key=body.license_key,
        fingerprint_hash=body.fingerprint_hash,
        server_ip=body.server_ip,
    )

    if not result.get("valid", False) and "error" in result:
        raise HTTPException(status_code=result.get("status", 400), detail=result["error"])

    return result


@router.post("/revoke")
@limiter.limit("5/minute")
async def api_revoke_license(
    request: Request,
    body: LicenseRevokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_superadmin),
):
    """Revoke a license. Requires superadmin access."""
    result = await revoke_license(
        db=db,
        license_key=body.license_key,
        reason=body.reason,
        actor_email=current_user.get("email"),
    )

    if "error" in result:
        raise HTTPException(status_code=result.get("status", 400), detail=result["error"])

    return result


@router.get("/info")
async def api_license_info(
    license_key: str = Query(..., description="License key to look up"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed information about a license. Requires authentication."""
    info = await get_license_info(db, license_key)
    if not info:
        raise HTTPException(status_code=404, detail="License not found")
    return info


@router.get("/status")
@limiter.limit("30/minute")
async def api_license_status(
    request: Request,
    license_key: str = Query(..., description="License key to check"),
    db: AsyncSession = Depends(get_db),
):
    """Quick status check for a license. No auth required, rate limited."""
    result = await validate_license(db=db, license_key=license_key)
    return {
        "license_key": license_key,
        "valid": result.get("valid", False),
        "status": result.get("status", "unknown"),
        "tier": result.get("tier"),
    }


@router.get("/list")
async def api_list_licenses(
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_superadmin),
):
    """List all licenses with pagination. Requires superadmin access."""
    licenses = await list_licenses(db, status=status, tier=tier, limit=limit, offset=offset)
    return {"licenses": licenses, "count": len(licenses), "limit": limit, "offset": offset}
