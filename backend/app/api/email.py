"""
HostingSignal Panel — Email Management API
Mail domains, accounts, spam protection.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user
from app.services.email_manager import EmailManager

router = APIRouter(prefix="/api/email", tags=["Email"])

email_mgr = EmailManager()


class CreateMailDomainRequest(BaseModel):
    domain: str


class CreateMailAccountRequest(BaseModel):
    email: str  # full address: user@domain.com
    password: str
    quota_mb: int = 1024  # 1GB default


class UpdateMailAccountRequest(BaseModel):
    email: str
    password: Optional[str] = None
    quota_mb: Optional[int] = None


class SpamFilterRequest(BaseModel):
    domain: str
    enabled: bool = True
    spam_score_threshold: float = 5.0


@router.get("/domains")
async def list_mail_domains(current_user: dict = Depends(get_current_user)):
    """List all mail domains."""
    try:
        domains = email_mgr.list_mail_domains()
        return {"domains": domains, "total": len(domains)}
    except Exception as e:
        return {"domains": [], "error": str(e)}


@router.post("/domains")
async def create_mail_domain(
    body: CreateMailDomainRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new mail domain."""
    try:
        result = email_mgr.create_mail_domain(body.domain)
        return {
            "status": "success",
            "domain": body.domain,
            "message": f"Mail domain {body.domain} created.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/domains/{domain}")
async def delete_mail_domain(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a mail domain and all its accounts."""
    try:
        result = email_mgr.delete_mail_domain(domain)
        return {"status": "success", "message": f"Mail domain {domain} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts")
async def list_mail_accounts(
    domain: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List email accounts, optionally filtered by domain."""
    try:
        accounts = email_mgr.list_mail_accounts(domain)
        return {"accounts": accounts, "total": len(accounts)}
    except Exception as e:
        return {"accounts": [], "error": str(e)}


@router.post("/accounts")
async def create_mail_account(
    body: CreateMailAccountRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new email account."""
    try:
        result = email_mgr.create_mail_account(
            body.email, body.password, body.quota_mb,
        )
        return {
            "status": "success",
            "email": body.email,
            "quota_mb": body.quota_mb,
            "message": f"Email account {body.email} created.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{email}")
async def delete_mail_account(
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete an email account."""
    try:
        result = email_mgr.delete_mail_account(email)
        return {"status": "success", "message": f"Account {email} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/accounts")
async def update_mail_account(
    body: UpdateMailAccountRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update email account password or quota."""
    try:
        result = email_mgr.update_mail_account(
            body.email, body.password, body.quota_mb,
        )
        return {"status": "success", "message": f"Account {body.email} updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spam-filter")
async def configure_spam_filter(
    body: SpamFilterRequest,
    current_user: dict = Depends(get_current_user),
):
    """Configure spam filter for a domain."""
    try:
        result = email_mgr.configure_spam_filter(
            body.domain, body.enabled, body.spam_score_threshold,
        )
        return {
            "status": "success",
            "domain": body.domain,
            "spam_filter": body.enabled,
            "threshold": body.spam_score_threshold,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
