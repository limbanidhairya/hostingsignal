"""System health and service status endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .deps import require_api_token
from ..service_manager import WebServerManager, DatabaseManager, MailManager, DNSManager, FTPManager

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(require_api_token)])

web = WebServerManager()
db = DatabaseManager()
mail = MailManager()
dns = DNSManager()
ftp = FTPManager()


@router.get("/status")
def system_status() -> dict:
    return {
        "success": True,
        "data": {
            "webserver": web.status(),
            "database": db.status(),
            "mail": mail.status(),
            "dns": dns.status(),
            "ftp": ftp.status(),
        },
    }
