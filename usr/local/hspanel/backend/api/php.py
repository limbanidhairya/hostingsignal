"""PHP version management endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from service_manager import PHPManager

router = APIRouter(prefix="/api/php", tags=["php"], dependencies=[Depends(require_api_token)])

php_mgr = PHPManager()


class PHPVersionRequest(BaseModel):
    version: str


class VhostPHPRequest(BaseModel):
    domain: str
    version: str


@router.get("/installed")
def installed_versions() -> dict:
    return {"success": True, "data": php_mgr.list_installed_versions()}


@router.get("/available")
def available_versions() -> dict:
    return {"success": True, "data": php_mgr.list_available_versions()}


@router.post("/install")
def install_version(req: PHPVersionRequest) -> dict:
    res = php_mgr.install_version(req.version)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/uninstall")
def uninstall_version(req: PHPVersionRequest) -> dict:
    res = php_mgr.uninstall_version(req.version)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/vhost/set")
def set_vhost_version(req: VhostPHPRequest) -> dict:
    res = php_mgr.set_vhost_php_version(req.domain, req.version)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()
