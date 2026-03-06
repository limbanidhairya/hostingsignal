from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.license import (
    License, LicenseLog, LicenseTier, LicenseStatus,
    TIER_CONFIG, generate_license_key, generate_hardware_fingerprint,
)
from app.schemas import (
    LicenseCreate, LicenseResponse, LicenseUpdate,
    LicenseValidate, LicenseValidationResponse,
    LicenseActivate, LicenseHeartbeat, LicenseStats,
)

router = APIRouter(prefix="/api/licenses", tags=["Licenses"])


def license_to_response(lic: License) -> LicenseResponse:
    config = TIER_CONFIG.get(lic.tier, TIER_CONFIG[LicenseTier.FREE])
    return LicenseResponse(
        id=lic.id,
        license_key=lic.license_key,
        customer_name=lic.customer_name,
        customer_email=lic.customer_email,
        tier=lic.tier.value,
        status=lic.status.value,
        max_domains=lic.max_domains,
        server_ip=lic.server_ip,
        server_hostname=lic.server_hostname,
        activated_at=lic.activated_at,
        last_heartbeat=lic.last_heartbeat,
        expires_at=lic.expires_at,
        created_at=lic.created_at,
        notes=lic.notes,
        monthly_revenue=lic.monthly_revenue,
        features=config["features"],
    )


# ===== Admin Endpoints =====

@router.get("/", response_model=list[LicenseResponse])
async def list_licenses(
    tier: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "reseller")),
):
    query = select(License)

    if tier:
        query = query.where(License.tier == LicenseTier(tier))
    if status_filter:
        query = query.where(License.status == LicenseStatus(status_filter))
    if search:
        query = query.where(
            (License.license_key.ilike(f"%{search}%")) |
            (License.customer_name.ilike(f"%{search}%")) |
            (License.customer_email.ilike(f"%{search}%"))
        )

    query = query.order_by(License.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    licenses = result.scalars().all()

    return [license_to_response(lic) for lic in licenses]


@router.post("/", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def issue_license(
    data: LicenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "reseller")),
):
    tier = LicenseTier(data.tier)
    config = TIER_CONFIG[tier]

    # Calculate expiry
    expires_at = None
    if data.validity_months > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.validity_months * 30)

    # Find or reference customer
    customer_result = await db.execute(select(User).where(User.email == data.customer_email))
    customer = customer_result.scalar_one_or_none()

    license = License(
        license_key=generate_license_key(),
        customer_id=customer.id if customer else None,
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        tier=tier,
        status=LicenseStatus.ACTIVE,
        max_domains=config["max_domains"],
        server_ip=data.server_ip,
        expires_at=expires_at,
        notes=data.notes,
    )
    db.add(license)
    await db.flush()

    # Log
    log = LicenseLog(
        license_id=license.id,
        action="issued",
        details=f"Issued by {current_user.email}, tier={tier.value}, validity={data.validity_months}mo",
    )
    db.add(log)
    await db.flush()

    return license_to_response(license)


@router.get("/stats", response_model=LicenseStats)
async def get_license_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "reseller")),
):
    result = await db.execute(select(License))
    all_licenses = result.scalars().all()

    tier_breakdown = {}
    for tier in LicenseTier:
        tier_breakdown[tier.value] = len([l for l in all_licenses if l.tier == tier])

    return LicenseStats(
        total=len(all_licenses),
        active=len([l for l in all_licenses if l.status == LicenseStatus.ACTIVE]),
        expired=len([l for l in all_licenses if l.status == LicenseStatus.EXPIRED]),
        suspended=len([l for l in all_licenses if l.status == LicenseStatus.SUSPENDED]),
        revoked=len([l for l in all_licenses if l.status == LicenseStatus.REVOKED]),
        monthly_revenue=sum(l.monthly_revenue for l in all_licenses),
        tier_breakdown=tier_breakdown,
    )


@router.get("/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "reseller")),
):
    result = await db.execute(select(License).where(License.id == license_id))
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    return license_to_response(license)


@router.put("/{license_id}", response_model=LicenseResponse)
async def update_license(
    license_id: int,
    data: LicenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(License).where(License.id == license_id))
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    changes = []

    if data.tier is not None:
        old_tier = license.tier.value
        license.tier = LicenseTier(data.tier)
        license.max_domains = TIER_CONFIG[license.tier]["max_domains"]
        changes.append(f"tier: {old_tier} -> {data.tier}")

    if data.status is not None:
        old_status = license.status.value
        license.status = LicenseStatus(data.status)
        changes.append(f"status: {old_status} -> {data.status}")

    if data.server_ip is not None:
        license.server_ip = data.server_ip
        changes.append(f"server_ip updated")

    if data.notes is not None:
        license.notes = data.notes

    if data.validity_months is not None:
        license.expires_at = datetime.now(timezone.utc) + timedelta(days=data.validity_months * 30)
        changes.append(f"expiry extended by {data.validity_months} months")

    # Log
    if changes:
        log = LicenseLog(
            license_id=license.id,
            action="updated",
            details=f"By {current_user.email}: {', '.join(changes)}",
        )
        db.add(log)

    await db.flush()
    return license_to_response(license)


@router.delete("/{license_id}")
async def revoke_license(
    license_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(License).where(License.id == license_id))
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    license.status = LicenseStatus.REVOKED
    log = LicenseLog(
        license_id=license.id,
        action="revoked",
        details=f"Revoked by {current_user.email}",
    )
    db.add(log)
    await db.flush()

    return {"message": f"License {license.license_key} revoked"}


# ===== Public License Validation Endpoints =====
# These endpoints are called by the panel installations to validate their license

@router.post("/validate", response_model=LicenseValidationResponse)
async def validate_license(
    data: LicenseValidate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate a license key against a server. Called by panel installations."""
    result = await db.execute(select(License).where(License.license_key == data.license_key))
    license = result.scalar_one_or_none()

    if not license:
        return LicenseValidationResponse(
            valid=False,
            license_key=data.license_key,
            tier="none",
            status="invalid",
            features=[],
            max_domains=0,
            message="Invalid license key",
        )

    # Check status
    if license.status == LicenseStatus.REVOKED:
        return LicenseValidationResponse(
            valid=False,
            license_key=data.license_key,
            tier=license.tier.value,
            status="revoked",
            features=[],
            max_domains=0,
            message="License has been revoked",
        )

    if license.status == LicenseStatus.SUSPENDED:
        return LicenseValidationResponse(
            valid=False,
            license_key=data.license_key,
            tier=license.tier.value,
            status="suspended",
            features=[],
            max_domains=0,
            message="License is suspended. Contact support.",
        )

    # Check expiry
    if license.expires_at and datetime.now(timezone.utc) > license.expires_at:
        license.status = LicenseStatus.EXPIRED
        log = LicenseLog(
            license_id=license.id,
            action="expired",
            ip_address=data.server_ip,
            details="Auto-expired during validation",
        )
        db.add(log)
        await db.flush()

        return LicenseValidationResponse(
            valid=False,
            license_key=data.license_key,
            tier=license.tier.value,
            status="expired",
            features=[],
            max_domains=0,
            expires_at=license.expires_at,
            message="License has expired. Please renew.",
        )

    # Check server IP binding
    if license.server_ip and license.server_ip != data.server_ip:
        return LicenseValidationResponse(
            valid=False,
            license_key=data.license_key,
            tier=license.tier.value,
            status="ip_mismatch",
            features=[],
            max_domains=0,
            message=f"License is bound to a different server ({license.server_ip})",
        )

    config = TIER_CONFIG[license.tier]

    return LicenseValidationResponse(
        valid=True,
        license_key=data.license_key,
        tier=license.tier.value,
        status="active",
        features=config["features"],
        max_domains=config["max_domains"],
        expires_at=license.expires_at,
        message="License is valid",
    )


@router.post("/activate", response_model=LicenseValidationResponse)
async def activate_license(
    data: LicenseActivate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Activate a license on a server. Called on first install."""
    result = await db.execute(select(License).where(License.license_key == data.license_key))
    license = result.scalar_one_or_none()

    if not license:
        return LicenseValidationResponse(
            valid=False, license_key=data.license_key, tier="none",
            status="invalid", features=[], max_domains=0, message="Invalid license key",
        )

    if not license.is_valid:
        return LicenseValidationResponse(
            valid=False, license_key=data.license_key, tier=license.tier.value,
            status=license.status.value, features=[], max_domains=0,
            message=f"License is {license.status.value}",
        )

    # Bind to server
    license.server_ip = data.server_ip
    license.server_hostname = data.server_hostname
    license.hardware_fingerprint = generate_hardware_fingerprint(data.server_ip, data.server_hostname or "")
    license.activated_at = datetime.now(timezone.utc)
    license.last_heartbeat = datetime.now(timezone.utc)

    log = LicenseLog(
        license_id=license.id,
        action="activated",
        ip_address=data.server_ip,
        details=f"Activated on {data.server_ip} ({data.server_hostname})",
    )
    db.add(log)
    await db.flush()

    config = TIER_CONFIG[license.tier]

    return LicenseValidationResponse(
        valid=True,
        license_key=data.license_key,
        tier=license.tier.value,
        status="active",
        features=config["features"],
        max_domains=config["max_domains"],
        expires_at=license.expires_at,
        message="License activated successfully",
    )


@router.post("/heartbeat")
async def license_heartbeat(
    data: LicenseHeartbeat,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Periodic heartbeat from panel installations (every 24h)."""
    result = await db.execute(select(License).where(License.license_key == data.license_key))
    license = result.scalar_one_or_none()

    if not license:
        return {"valid": False, "message": "Invalid license key"}

    if license.server_ip and license.server_ip != data.server_ip:
        return {"valid": False, "message": "IP mismatch"}

    # Check expiry
    if license.expires_at and datetime.now(timezone.utc) > license.expires_at:
        license.status = LicenseStatus.EXPIRED
        await db.flush()
        return {"valid": False, "message": "License expired"}

    # Update heartbeat
    license.last_heartbeat = datetime.now(timezone.utc)

    log = LicenseLog(
        license_id=license.id,
        action="heartbeat",
        ip_address=data.server_ip,
    )
    db.add(log)
    await db.flush()

    return {
        "valid": True,
        "tier": license.tier.value,
        "features": TIER_CONFIG[license.tier]["features"],
        "expires_at": license.expires_at.isoformat() if license.expires_at else None,
        "message": "Heartbeat received",
    }


@router.post("/deactivate")
async def deactivate_license(
    data: LicenseActivate,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate (unbind) a license from a server."""
    result = await db.execute(select(License).where(License.license_key == data.license_key))
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    if license.server_ip != data.server_ip:
        raise HTTPException(status_code=403, detail="Server IP does not match")

    license.server_ip = None
    license.server_hostname = None
    license.hardware_fingerprint = None

    log = LicenseLog(
        license_id=license.id,
        action="deactivated",
        ip_address=data.server_ip,
        details=f"Deactivated from {data.server_ip}",
    )
    db.add(log)
    await db.flush()

    return {"message": "License deactivated successfully"}


# ===== License Transfer =====

@router.post("/transfer")
async def transfer_license(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Transfer a license from old server to new server.
    - Keeps the same license key
    - Re-binds to new server IP
    - Marks old server as panel_disabled
    - Logs the transfer with old server details
    """
    license_key = data.get("license_key")
    old_server_ip = data.get("old_server_ip")
    new_server_ip = data.get("new_server_ip") or request.client.host

    if not license_key:
        raise HTTPException(400, "license_key is required")

    result = await db.execute(select(License).where(License.license_key == license_key))
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(404, "License not found")

    # Verify old server IP matches current binding
    if license.server_ip and old_server_ip and license.server_ip != old_server_ip:
        raise HTTPException(403, f"License is bound to {license.server_ip}, not {old_server_ip}")

    if license.status == LicenseStatus.REVOKED:
        raise HTTPException(403, "Cannot transfer a revoked license")

    if license.status == LicenseStatus.SUSPENDED:
        raise HTTPException(403, "Cannot transfer a suspended license")

    # Perform transfer
    old_ip = license.server_ip
    old_hostname = license.server_hostname

    # Update with new server info
    license.transferred_from = old_ip
    license.transfer_date = datetime.now(timezone.utc)
    license.transfer_count = (license.transfer_count or 0) + 1
    license.server_ip = new_server_ip
    license.server_hostname = data.get("new_server_hostname", "")
    license.hardware_fingerprint = generate_hardware_fingerprint(
        new_server_ip, license.server_hostname or ""
    )
    license.activated_at = datetime.now(timezone.utc)
    license.last_heartbeat = datetime.now(timezone.utc)
    license.panel_disabled = False  # New server is active

    # Log the transfer
    log = LicenseLog(
        license_id=license.id,
        action="transferred",
        ip_address=new_server_ip,
        details=f"Transferred from {old_ip} ({old_hostname}) to {new_server_ip}. Transfer #{license.transfer_count}",
    )
    db.add(log)
    await db.flush()

    config = TIER_CONFIG[license.tier]

    return {
        "status": "transferred",
        "license_key": license.license_key,
        "old_server_ip": old_ip,
        "new_server_ip": new_server_ip,
        "transfer_count": license.transfer_count,
        "tier": license.tier.value,
        "features": config["features"],
        "message": f"License transferred successfully. Old server ({old_ip}) panel will be disabled on next heartbeat.",
    }


@router.get("/check-disabled/{license_key}")
async def check_panel_disabled(
    license_key: str,
    server_ip: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if the panel on this server should be disabled.
    Called by panel installations on heartbeat to check if the license
    has been transferred away from this server.
    """
    result = await db.execute(select(License).where(License.license_key == license_key))
    license = result.scalar_one_or_none()

    if not license:
        return {"disabled": True, "reason": "License not found"}

    # If license is bound to a DIFFERENT server, this server's panel should be disabled
    if license.server_ip and license.server_ip != server_ip:
        return {
            "disabled": True,
            "reason": "License has been transferred to another server",
            "transferred_to": license.server_ip,
            "transfer_date": license.transfer_date.isoformat() if license.transfer_date else None,
        }

    if license.panel_disabled:
        return {"disabled": True, "reason": "Panel has been disabled by administrator"}

    return {"disabled": False}
