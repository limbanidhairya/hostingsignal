"""Compatibility endpoints for legacy and external API paths."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from service_manager import DatabaseManager, MailManager, WebServerManager, DNSManager, SSLManager, FTPManager

router = APIRouter(prefix="/api", tags=["compat"], dependencies=[Depends(require_api_token)])

_db = DatabaseManager()
_mail = MailManager()
_web = WebServerManager()
_dns = DNSManager()
_ssl = SSLManager()
_ftp = FTPManager()


class CompatDatabaseCreateRequest(BaseModel):
    name: str


class CompatEmailCreateRequest(BaseModel):
    email: str | None = None
    user: str | None = None
    domain: str | None = None
    password: str
    quota_mb: int = 500


class CompatDomainCreateRequest(BaseModel):
    domain: str
    php_version: str = "lsphp83"
    docroot: str | None = None
    server_ip: str | None = None
    create_dns: bool = True
    create_ssl: bool = False
    admin_email: str = "admin@example.com"


class CompatDnsCreateZoneRequest(BaseModel):
    domain: str
    ns1: str = "ns1.yourdomain.com"
    ns2: str = "ns2.yourdomain.com"
    admin_email: str = "hostmaster@example.com"
    server_ip: str = ""


class CompatFtpCreateRequest(BaseModel):
    username: str
    password: str
    home: str | None = None
    path: str | None = None
    domain: str | None = None
    system_user: str = "hspanel"


@router.post("/database/create")
def compat_database_create(req: CompatDatabaseCreateRequest) -> dict:
    res = _db.create_database(req.name)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/email/create")
def compat_email_create(req: CompatEmailCreateRequest) -> dict:
    email = (req.email or "").strip()
    if not email:
        if not req.user or not req.domain:
            raise HTTPException(status_code=400, detail="Provide either email or user+domain")
        email = f"{req.user}@{req.domain}"

    res = _mail.create_mailbox(email, req.password, req.quota_mb)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/domain/create")
def compat_domain_create(req: CompatDomainCreateRequest) -> dict:
    vhost = _web.create_vhost(req.domain, php_version=req.php_version, docroot=req.docroot)
    if not vhost.success:
        raise HTTPException(status_code=400, detail=vhost.message)

    out: dict = {"vhost": vhost.to_dict()}

    if req.create_dns:
        zone = _dns.create_zone(req.domain, req.ns1, req.ns2, req.admin_email, req.server_ip or "")
        out["dns"] = zone.to_dict()

    if req.create_ssl:
        cert = _ssl.issue_cert(req.domain, req.admin_email)
        out["ssl"] = cert.to_dict()

    return {"success": True, "message": f"Domain provisioned: {req.domain}", "data": out}


@router.post("/dns/create-zone")
def compat_dns_create_zone(req: CompatDnsCreateZoneRequest) -> dict:
    res = _dns.create_zone(req.domain, req.ns1, req.ns2, req.admin_email, req.server_ip)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/ftp/create")
def compat_ftp_create(req: CompatFtpCreateRequest) -> dict:
    home = req.home or req.path
    if not home:
        if req.domain:
            home = f"/home/{req.system_user}/public_html/{req.domain}"
        else:
            home = f"/home/{req.system_user}/public_html"

    res = _ftp.create_ftp_user(req.username, req.password, home, req.system_user)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()
