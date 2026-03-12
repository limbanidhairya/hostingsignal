"""Mail domain/mailbox endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from ..service_manager import MailManager

router = APIRouter(prefix="/api/mail", tags=["mail"], dependencies=[Depends(require_api_token)])

mail_mgr = MailManager()


class MailDomainRequest(BaseModel):
    domain: str


class MailboxCreateRequest(BaseModel):
    email: str
    password: str | None = None
    quota_mb: int = 500


class MailboxPasswordRequest(BaseModel):
    email: str
    new_password: str


@router.post("/domain/create")
def create_domain(req: MailDomainRequest) -> dict:
    res = mail_mgr.add_mail_domain(req.domain)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.delete("/domain/{domain}")
def delete_domain(domain: str) -> dict:
    res = mail_mgr.remove_mail_domain(domain)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/domain/list")
def list_domains() -> dict:
    return {"success": True, "data": mail_mgr.list_mail_domains()}


@router.post("/mailbox/create")
def create_mailbox(req: MailboxCreateRequest) -> dict:
    res = mail_mgr.create_mailbox(req.email, req.password, req.quota_mb)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.delete("/mailbox/{email}")
def delete_mailbox(email: str) -> dict:
    res = mail_mgr.delete_mailbox(email)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/mailbox/list")
def list_mailboxes(domain: str | None = None) -> dict:
    return {"success": True, "data": mail_mgr.list_mailboxes(domain)}


@router.post("/mailbox/password")
def change_password(req: MailboxPasswordRequest) -> dict:
    res = mail_mgr.change_mailbox_password(req.email, req.new_password)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()
