"""Security controls endpoints (CSF + ModSecurity)."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from service_manager import SecurityManager

router = APIRouter(prefix="/api/security", tags=["security"], dependencies=[Depends(require_api_token)])

sec_mgr = SecurityManager()


class IPRequest(BaseModel):
    ip: str
    comment: str = "HS-Panel"


class ModSecModeRequest(BaseModel):
    mode: str


class RuleRequest(BaseModel):
    rule_id: str


@router.get("/status")
def status() -> dict:
    return {"success": True, "data": sec_mgr.status()}


@router.post("/csf/enable")
def enable_csf() -> dict:
    res = sec_mgr.enable_csf()
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/csf/disable")
def disable_csf() -> dict:
    res = sec_mgr.disable_csf()
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/csf/allow")
def allow_ip(req: IPRequest) -> dict:
    res = sec_mgr.allow_ip(req.ip, req.comment)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/csf/deny")
def deny_ip(req: IPRequest) -> dict:
    res = sec_mgr.deny_ip(req.ip, req.comment)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/csf/remove")
def remove_ip(req: IPRequest) -> dict:
    res = sec_mgr.remove_ip(req.ip)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/modsec/status")
def modsec_status() -> dict:
    res = sec_mgr.modsec_status()
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/modsec/mode")
def modsec_mode(req: ModSecModeRequest) -> dict:
    res = sec_mgr.set_modsec_mode(req.mode)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/modsec/rule/disable")
def disable_rule(req: RuleRequest) -> dict:
    res = sec_mgr.disable_rule(req.rule_id)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/modsec/rule/enable")
def enable_rule(req: RuleRequest) -> dict:
    res = sec_mgr.enable_rule(req.rule_id)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()
