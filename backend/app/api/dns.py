"""
HostingSignal Panel — DNS Management API
Zone editor, record management, nameserver management.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.core.security import get_current_user
from app.services.dns_manager import DNSManager

router = APIRouter(prefix="/api/dns", tags=["DNS Management"])

dns_mgr = DNSManager()


class DNSRecordRequest(BaseModel):
    domain: str
    record_type: str  # A, AAAA, CNAME, MX, TXT, NS, SRV, CAA
    name: str         # e.g., "@", "www", "mail"
    value: str        # Record value
    ttl: int = 3600
    priority: Optional[int] = None  # For MX records


class UpdateRecordRequest(BaseModel):
    domain: str
    record_id: str
    record_type: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    ttl: Optional[int] = None
    priority: Optional[int] = None


@router.get("/zones")
async def list_dns_zones(current_user: dict = Depends(get_current_user)):
    """List all DNS zones."""
    try:
        zones = dns_mgr.list_zones()
        return {"zones": zones, "total": len(zones)}
    except Exception as e:
        return {"zones": [], "error": str(e)}


@router.get("/zone/{domain}")
async def get_zone_records(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Get all DNS records for a zone."""
    try:
        records = dns_mgr.get_zone_records(domain)
        return {
            "domain": domain,
            "records": records,
            "total": len(records),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record")
async def add_dns_record(
    body: DNSRecordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a DNS record to a zone."""
    valid_types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", "CAA", "PTR"]
    if body.record_type.upper() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Must be one of: {', '.join(valid_types)}",
        )

    try:
        result = dns_mgr.add_record(
            zone=body.domain,
            record_type=body.record_type.upper(),
            value=body.value,
            name=body.name,
            ttl=body.ttl,
            priority=body.priority,
        )
        return {
            "status": "success",
            "domain": body.domain,
            "record": {
                "type": body.record_type.upper(),
                "name": body.name,
                "value": body.value,
                "ttl": body.ttl,
            },
            "message": f"{body.record_type.upper()} record added.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/record")
async def update_dns_record(
    body: UpdateRecordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing DNS record."""
    try:
        result = dns_mgr.update_record(
            zone=body.domain,
            record_id=body.record_id,
            record_type=body.record_type,
            name=body.name,
            value=body.value,
            ttl=body.ttl,
        )
        return {"status": "success", "message": "Record updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/record/{domain}/{record_id}")
async def delete_dns_record(
    domain: str,
    record_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a DNS record."""
    try:
        result = dns_mgr.delete_record(domain, record_id)
        return {"status": "success", "message": f"Record {record_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zone/{domain}/import")
async def import_zone_file(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Import a BIND-format zone file."""
    return {"status": "info", "message": "Zone import endpoint — coming soon"}


@router.get("/zone/{domain}/export")
async def export_zone_file(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Export zone as BIND-format zone file."""
    try:
        records = dns_mgr.get_zone_records(domain)
        zone_content = f"; Zone file for {domain}\n"
        zone_content += f"$ORIGIN {domain}.\n$TTL 3600\n\n"
        for rec in records:
            name = rec.get("name", "@")
            rtype = rec.get("type", "A")
            value = rec.get("value", "")
            ttl = rec.get("ttl", 3600)
            zone_content += f"{name}\t{ttl}\tIN\t{rtype}\t{value}\n"

        return {"domain": domain, "zone_file": zone_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
