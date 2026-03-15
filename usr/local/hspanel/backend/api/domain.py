"""Domain and vhost lifecycle endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from service_manager import WebServerManager, DNSManager, SSLManager

router = APIRouter(prefix="/api/domain", tags=["domain"], dependencies=[Depends(require_api_token)])

web = WebServerManager()
dns = DNSManager()
ssl = SSLManager()


class DomainCreateRequest(BaseModel):
    domain: str
    php_version: str = "lsphp83"
    docroot: str | None = None
    server_ip: str | None = None
    create_dns: bool = True
    create_ssl: bool = False
    admin_email: str = Field(default="admin@example.com")


@router.post("/create")
def create_domain(req: DomainCreateRequest) -> dict:
    vhost = web.create_vhost(req.domain, php_version=req.php_version, docroot=req.docroot)
    if not vhost.success:
        raise HTTPException(status_code=400, detail=vhost.message)

    out: dict = {"vhost": vhost.to_dict()}

    if req.create_dns:
        zone = dns.create_zone(req.domain, server_ip=req.server_ip or "")
        out["dns"] = zone.to_dict()

    if req.create_ssl:
        cert = ssl.issue_cert(req.domain, req.admin_email)
        out["ssl"] = cert.to_dict()

    return {"success": True, "message": f"Domain provisioned: {req.domain}", "data": out}


@router.delete("/{domain}")
def delete_domain(domain: str) -> dict:
    res = web.delete_vhost(domain)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/list")
def list_domains() -> dict:
    return {"success": True, "data": web.list_vhosts()}
