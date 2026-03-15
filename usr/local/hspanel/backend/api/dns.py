"""DNS zone and record endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from service_manager import DNSManager

router = APIRouter(prefix="/api/dns", tags=["dns"], dependencies=[Depends(require_api_token)])

dns_mgr = DNSManager()


class ZoneCreateRequest(BaseModel):
    domain: str
    ns1: str = "ns1.yourdomain.com"
    ns2: str = "ns2.yourdomain.com"
    admin_email: str = "hostmaster@example.com"
    server_ip: str = ""


class RecordRequest(BaseModel):
    domain: str
    name: str
    record_type: str
    content: str
    ttl: int = 300


@router.post("/zone/create")
def create_zone(req: ZoneCreateRequest) -> dict:
    res = dns_mgr.create_zone(req.domain, req.ns1, req.ns2, req.admin_email, req.server_ip)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.delete("/zone/{domain}")
def delete_zone(domain: str) -> dict:
    res = dns_mgr.delete_zone(domain)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/zone/list")
def list_zones() -> dict:
    return {"success": True, "data": dns_mgr.list_zones()}


@router.post("/record/add")
def add_record(req: RecordRequest) -> dict:
    res = dns_mgr.add_record(req.domain, req.name, req.record_type, req.content, req.ttl)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/record/delete")
def delete_record(req: RecordRequest) -> dict:
    res = dns_mgr.delete_record(req.domain, req.name, req.record_type)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()
