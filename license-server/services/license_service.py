"""
HostingSignal License Server — License Service
Core business logic for license CRUD and validation.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    License, Activation, AuditLog,
    LicenseTier, LicenseStatus, ActivationStatus, TIER_CONFIG,
)
from auth.jwt_handler import create_license_token
from utils.crypto import generate_license_key, hash_fingerprint


async def create_license(
    db: AsyncSession,
    customer_email: str,
    tier: str = "starter",
    customer_name: Optional[str] = None,
    bound_ip: Optional[str] = None,
    bound_domain: Optional[str] = None,
    max_activations: int = 1,
    expires_days: Optional[int] = None,
    notes: Optional[str] = None,
    created_by: Optional[UUID] = None,
) -> License:
    """Create a new license key."""
    license_key = generate_license_key()
    expires_at = None
    if expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

    license_obj = License(
        license_key=license_key,
        customer_email=customer_email,
        customer_name=customer_name,
        tier=LicenseTier(tier),
        status=LicenseStatus.ACTIVE,
        bound_ip=bound_ip,
        bound_domain=bound_domain,
        max_activations=max_activations,
        expires_at=expires_at,
        notes=notes,
        created_by=created_by,
    )
    db.add(license_obj)

    # Audit log
    db.add(AuditLog(
        action="create",
        license_key=license_key,
        actor_email=customer_email,
        details={"tier": tier, "bound_ip": bound_ip, "bound_domain": bound_domain},
    ))

    await db.flush()
    return license_obj


async def activate_license(
    db: AsyncSession,
    license_key: str,
    server_ip: str,
    hostname: Optional[str] = None,
    cpu_id: Optional[str] = None,
    disk_uuid: Optional[str] = None,
    mac_address: Optional[str] = None,
    machine_id: Optional[str] = None,
) -> dict:
    """Activate a license on a specific server. Returns signed token."""
    # Find license
    result = await db.execute(
        select(License).where(License.license_key == license_key)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return {"error": "License key not found", "status": 404}

    if license_obj.status != LicenseStatus.ACTIVE:
        return {"error": f"License is {license_obj.status.value}", "status": 403}

    # Check expiry
    if license_obj.expires_at and license_obj.expires_at < datetime.now(timezone.utc):
        license_obj.status = LicenseStatus.EXPIRED
        return {"error": "License has expired", "status": 403}

    # Check IP binding
    if license_obj.bound_ip and license_obj.bound_ip != server_ip:
        return {"error": "License is bound to a different IP address", "status": 403}

    # Check activation count
    active_count = await db.execute(
        select(func.count(Activation.id)).where(
            and_(
                Activation.license_id == license_obj.id,
                Activation.status == ActivationStatus.ACTIVE,
            )
        )
    )
    count = active_count.scalar() or 0
    if count >= license_obj.max_activations:
        return {"error": "Maximum activations reached. Deactivate an existing activation first.", "status": 403}

    # Create fingerprint hash
    fp_hash = hash_fingerprint(
        cpu_id or "", disk_uuid or "", mac_address or "",
        hostname or "", machine_id or "",
    )

    # Check if already activated with this fingerprint
    existing = await db.execute(
        select(Activation).where(
            and_(
                Activation.license_id == license_obj.id,
                Activation.fingerprint_hash == fp_hash,
            )
        )
    )
    existing_activation = existing.scalar_one_or_none()

    if existing_activation and existing_activation.status == ActivationStatus.ACTIVE:
        # Re-issue token for existing activation
        token = create_license_token(license_key, fp_hash, license_obj.tier.value)
        existing_activation.signed_token = token
        existing_activation.last_check_in = datetime.now(timezone.utc)
        return {
            "license_key": license_key,
            "signed_token": token,
            "tier": license_obj.tier.value,
            "status": "reactivated",
            "message": "License re-validated on existing server.",
        }

    # Create new activation
    token = create_license_token(license_key, fp_hash, license_obj.tier.value)

    activation = Activation(
        license_id=license_obj.id,
        server_ip=server_ip,
        hostname=hostname,
        cpu_id=cpu_id,
        disk_uuid=disk_uuid,
        mac_address=mac_address,
        machine_id=machine_id,
        fingerprint_hash=fp_hash,
        signed_token=token,
        status=ActivationStatus.ACTIVE,
    )
    db.add(activation)

    # Update license
    license_obj.last_validated_at = datetime.now(timezone.utc)
    if not license_obj.bound_ip:
        license_obj.bound_ip = server_ip

    # Audit log
    db.add(AuditLog(
        action="activate",
        license_key=license_key,
        ip_address=server_ip,
        details={"hostname": hostname, "fingerprint_hash": fp_hash},
    ))

    await db.flush()
    return {
        "license_key": license_key,
        "signed_token": token,
        "tier": license_obj.tier.value,
        "status": "activated",
        "message": "License activated successfully.",
    }


async def validate_license(
    db: AsyncSession,
    license_key: str,
    fingerprint_hash: Optional[str] = None,
    server_ip: Optional[str] = None,
) -> dict:
    """Validate a license key. Optionally verify against fingerprint/IP."""
    result = await db.execute(
        select(License).where(License.license_key == license_key)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return {"valid": False, "error": "License key not found", "status": 404}

    if license_obj.status != LicenseStatus.ACTIVE:
        return {"valid": False, "error": f"License is {license_obj.status.value}", "status": 403}

    if license_obj.expires_at and license_obj.expires_at < datetime.now(timezone.utc):
        license_obj.status = LicenseStatus.EXPIRED
        return {"valid": False, "error": "License has expired", "status": 403}

    # If fingerprint provided, verify activation
    if fingerprint_hash:
        activation = await db.execute(
            select(Activation).where(
                and_(
                    Activation.license_id == license_obj.id,
                    Activation.fingerprint_hash == fingerprint_hash,
                    Activation.status == ActivationStatus.ACTIVE,
                )
            )
        )
        act = activation.scalar_one_or_none()
        if not act:
            return {"valid": False, "error": "No active activation matches this fingerprint", "status": 403}
        act.last_check_in = datetime.now(timezone.utc)

    # Update last validated
    license_obj.last_validated_at = datetime.now(timezone.utc)

    # Audit
    db.add(AuditLog(
        action="validate",
        license_key=license_key,
        ip_address=server_ip,
        details={"fingerprint_hash": fingerprint_hash},
    ))

    tier_config = TIER_CONFIG.get(license_obj.tier, {})
    return {
        "valid": True,
        "license_key": license_key,
        "tier": license_obj.tier.value,
        "tier_config": tier_config,
        "status": license_obj.status.value,
        "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
    }


async def revoke_license(
    db: AsyncSession,
    license_key: str,
    reason: Optional[str] = None,
    actor_email: Optional[str] = None,
) -> dict:
    """Revoke a license and deactivate all activations."""
    result = await db.execute(
        select(License).where(License.license_key == license_key)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return {"error": "License key not found", "status": 404}

    license_obj.status = LicenseStatus.REVOKED

    # Deactivate all activations
    activations = await db.execute(
        select(Activation).where(
            and_(
                Activation.license_id == license_obj.id,
                Activation.status == ActivationStatus.ACTIVE,
            )
        )
    )
    for act in activations.scalars().all():
        act.status = ActivationStatus.DEACTIVATED
        act.deactivated_at = datetime.now(timezone.utc)

    # Audit
    db.add(AuditLog(
        action="revoke",
        license_key=license_key,
        actor_email=actor_email,
        details={"reason": reason},
    ))

    await db.flush()
    return {"status": "revoked", "message": f"License {license_key} has been revoked."}


async def get_license_info(db: AsyncSession, license_key: str) -> Optional[dict]:
    """Get detailed license info including activations."""
    result = await db.execute(
        select(License).where(License.license_key == license_key)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return None

    active_acts = [a for a in license_obj.activations if a.status == ActivationStatus.ACTIVE]

    return {
        "license_key": license_obj.license_key,
        "customer_email": license_obj.customer_email,
        "customer_name": license_obj.customer_name,
        "tier": license_obj.tier.value,
        "status": license_obj.status.value,
        "bound_ip": license_obj.bound_ip,
        "bound_domain": license_obj.bound_domain,
        "max_activations": license_obj.max_activations,
        "active_activations": len(active_acts),
        "issued_at": license_obj.issued_at.isoformat() if license_obj.issued_at else None,
        "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
        "last_validated_at": license_obj.last_validated_at.isoformat() if license_obj.last_validated_at else None,
        "activations": [
            {
                "server_ip": a.server_ip,
                "hostname": a.hostname,
                "status": a.status.value,
                "activated_at": a.activated_at.isoformat() if a.activated_at else None,
                "last_check_in": a.last_check_in.isoformat() if a.last_check_in else None,
            }
            for a in license_obj.activations
        ],
    }


async def list_licenses(
    db: AsyncSession,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    """List licenses with optional filtering."""
    query = select(License)
    if status:
        query = query.where(License.status == LicenseStatus(status))
    if tier:
        query = query.where(License.tier == LicenseTier(tier))
    query = query.order_by(License.issued_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    licenses = result.scalars().all()

    return [
        {
            "license_key": lic.license_key,
            "customer_email": lic.customer_email,
            "tier": lic.tier.value,
            "status": lic.status.value,
            "issued_at": lic.issued_at.isoformat() if lic.issued_at else None,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
            "active_activations": len([a for a in lic.activations if a.status == ActivationStatus.ACTIVE]),
        }
        for lic in licenses
    ]
