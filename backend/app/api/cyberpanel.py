"""
CyberPanel API Proxy — Bridges HostingSignal frontend to CyberPanel backend.
This module wraps CyberPanel's REST API so the frontend communicates through
our own API layer, allowing license checks and feature gating.
"""

import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/panel", tags=["CyberPanel Proxy"])


async def cyberpanel_request(
    endpoint: str,
    method: str = "POST",
    data: dict = None,
) -> dict:
    """Make an authenticated request to CyberPanel's API."""
    if not settings.CYBERPANEL_URL:
        raise HTTPException(
            status_code=503,
            detail="CyberPanel not configured. Set CYBERPANEL_URL in environment.",
        )

    url = f"{settings.CYBERPANEL_URL}/api/{endpoint}"

    payload = {
        "adminUser": settings.CYBERPANEL_ADMIN_USER,
        "adminPass": settings.CYBERPANEL_ADMIN_PASS,
    }
    if data:
        payload.update(data)

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        try:
            if method == "POST":
                response = await client.post(url, json=payload)
            else:
                response = await client.get(url, params=payload)

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"CyberPanel API error: {str(e)}",
            )


# ===== Website Management =====

@router.post("/websites/create")
async def create_website(
    domain: str,
    package: str = "Default",
    admin_email: str = "",
    php_version: str = "8.1",
    ssl: bool = True,
    current_user: User = Depends(get_current_user),
):
    result = await cyberpanel_request("createWebsite", data={
        "domainName": domain,
        "package": package,
        "adminEmail": admin_email or current_user.email,
        "phpSelection": f"PHP {php_version}",
        "ssl": 1 if ssl else 0,
    })
    return result


@router.get("/websites/list")
async def list_websites(current_user: User = Depends(get_current_user)):
    result = await cyberpanel_request("listWebsites")
    return result


@router.post("/websites/delete")
async def delete_website(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    result = await cyberpanel_request("deleteWebsite", data={
        "domainName": domain,
    })
    return result


# ===== Email Management =====

@router.post("/email/create")
async def create_email(
    domain: str,
    username: str,
    password: str,
    current_user: User = Depends(get_current_user),
):
    result = await cyberpanel_request("createEmail", data={
        "domainName": domain,
        "userName": username,
        "password": password,
    })
    return result


@router.get("/email/list")
async def list_emails(domain: str, current_user: User = Depends(get_current_user)):
    result = await cyberpanel_request("getEmailAccounts", data={
        "domainName": domain,
    })
    return result


# ===== Database Management =====

@router.post("/databases/create")
async def create_database(
    domain: str,
    db_name: str,
    db_user: str,
    db_password: str,
    current_user: User = Depends(get_current_user),
):
    result = await cyberpanel_request("createDatabase", data={
        "databaseWebsite": domain,
        "dbName": db_name,
        "dbUsername": db_user,
        "dbPassword": db_password,
    })
    return result


@router.get("/databases/list")
async def list_databases(domain: str, current_user: User = Depends(get_current_user)):
    result = await cyberpanel_request("listDatabases", data={
        "databaseWebsite": domain,
    })
    return result


# ===== DNS Management =====

@router.post("/dns/create-record")
async def create_dns_record(
    domain: str,
    name: str,
    record_type: str,
    value: str,
    ttl: int = 3600,
    priority: int = 0,
    current_user: User = Depends(get_current_user),
):
    result = await cyberpanel_request("addDNSRecord", data={
        "domainName": domain,
        "recordName": name,
        "recordType": record_type,
        "recordContent": value,
        "TTL": ttl,
        "priority": priority,
    })
    return result


@router.get("/dns/records")
async def list_dns_records(domain: str, current_user: User = Depends(get_current_user)):
    result = await cyberpanel_request("getCurrentRecordsForDomain", data={
        "domainName": domain,
    })
    return result


# ===== SSL =====

@router.post("/ssl/issue")
async def issue_ssl(domain: str, current_user: User = Depends(get_current_user)):
    result = await cyberpanel_request("issueSSL", data={
        "domainName": domain,
    })
    return result


# ===== Backups =====

@router.post("/backups/create")
async def create_backup(domain: str, current_user: User = Depends(get_current_user)):
    result = await cyberpanel_request("submitBackupCreation", data={
        "websiteToBeBacked": domain,
    })
    return result


# ===== Server Info =====

@router.get("/server/status")
async def server_status(current_user: User = Depends(get_current_user)):
    """Get basic server information."""
    try:
        result = await cyberpanel_request("getServerStatus")
        return result
    except HTTPException:
        # Return mock data if CyberPanel isn't connected
        return {
            "status": "demo_mode",
            "cpu": "34%",
            "ram": "62%",
            "disk": "45%",
            "uptime": "15 days",
            "message": "CyberPanel not connected — showing demo data",
        }
