"""SSL certificate endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from service_manager import SSLManager

router = APIRouter(prefix="/api/ssl", tags=["ssl"], dependencies=[Depends(require_api_token)])

ssl_mgr = SSLManager()


class IssueCertRequest(BaseModel):
    domain: str
    admin_email: str
    webroot: str = "/var/www/letsencrypt"
    staging: bool = False


class RenewCertRequest(BaseModel):
    domain: str | None = None


class RevokeCertRequest(BaseModel):
    domain: str


@router.post("/issue")
def issue_cert(req: IssueCertRequest) -> dict:
    res = ssl_mgr.issue_cert(req.domain, req.admin_email, req.webroot, req.staging)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/renew")
def renew(req: RenewCertRequest) -> dict:
    res = ssl_mgr.renew_cert(req.domain)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/revoke")
def revoke(req: RevokeCertRequest) -> dict:
    res = ssl_mgr.revoke_cert(req.domain)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/list")
def list_certs() -> dict:
    return {"success": True, "data": ssl_mgr.list_certs()}
