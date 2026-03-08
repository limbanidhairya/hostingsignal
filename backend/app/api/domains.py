"""
HostingSignal Panel — Domain Management API
Domain CRUD, nameserver configuration.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.core.security import get_current_user
from app.services.dns_manager import DNSManager

router = APIRouter(prefix="/api/domains", tags=["Domains"])

dns_mgr = DNSManager()


class AddDomainRequest(BaseModel):
    domain: str
    nameservers: Optional[List[str]] = None


class UpdateNameserversRequest(BaseModel):
    domain: str
    nameservers: List[str]


@router.get("/")
async def list_domains(current_user: dict = Depends(get_current_user)):
    """List all managed domains."""
    try:
        domains = dns_mgr.list_zones()
        return {"domains": domains, "total": len(domains)}
    except Exception as e:
        return {"domains": [], "total": 0, "warning": str(e)}


@router.post("/add")
async def add_domain(
    body: AddDomainRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a new domain to management."""
    try:
        result = dns_mgr.create_zone(body.domain)
        if body.nameservers:
            for ns in body.nameservers:
                dns_mgr.add_record(body.domain, "NS", ns)
        return {
            "status": "success",
            "domain": body.domain,
            "message": f"Domain {body.domain} added successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{domain}")
async def remove_domain(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a domain from management."""
    try:
        result = dns_mgr.delete_zone(domain)
        return {
            "status": "success",
            "domain": domain,
            "message": f"Domain {domain} removed.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{domain}")
async def get_domain_info(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Get detailed information about a domain."""
    try:
        records = dns_mgr.get_zone_records(domain)
        return {
            "domain": domain,
            "records": records,
            "total_records": len(records),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nameservers")
async def update_nameservers(
    body: UpdateNameserversRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update nameservers for a domain."""
    try:
        # Remove existing NS records
        existing = dns_mgr.get_zone_records(body.domain)
        for rec in existing:
            if rec.get("type") == "NS":
                dns_mgr.delete_record(body.domain, rec.get("id", ""))

        # Add new NS records
        for ns in body.nameservers:
            dns_mgr.add_record(body.domain, "NS", ns)

        return {
            "status": "success",
            "domain": body.domain,
            "nameservers": body.nameservers,
            "message": "Nameservers updated.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
