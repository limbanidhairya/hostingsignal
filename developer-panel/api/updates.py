"""Developer Panel — Update Push API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import secrets

router = APIRouter(prefix="/api/updates", tags=["Updates"])

_releases: list = []


class CreateReleaseRequest(BaseModel):
    version: str
    channel: str = "stable"  # stable | beta | dev
    changelog: str = ""
    min_current_version: Optional[str] = None
    archive_url: Optional[str] = None


@router.post("/release")
async def create_release(body: CreateReleaseRequest):
    """Push a new panel release."""
    release = {
        "id": f"rel_{secrets.token_hex(6)}",
        "version": body.version,
        "channel": body.channel,
        "changelog": body.changelog,
        "min_current_version": body.min_current_version,
        "archive_url": body.archive_url or f"https://updates.hostingsignal.com/{body.channel}/hostingsignal-{body.version}.tar.gz",
        "released_at": datetime.now(timezone.utc).isoformat(),
        "download_count": 0,
    }
    _releases.insert(0, release)
    return {"status": "success", "release": release}


@router.get("/latest/{channel}")
async def latest_release(channel: str = "stable"):
    """Get latest version for a channel."""
    for r in _releases:
        if r["channel"] == channel:
            return r
    return {"version": "1.0.0", "channel": channel, "message": "No releases found"}


@router.get("/check")
async def check_update(current_version: str, channel: str = "stable"):
    """Check if update is available."""
    for r in _releases:
        if r["channel"] == channel:
            if r["version"] > current_version:
                return {"update_available": True, "latest": r["version"], "download_url": r["archive_url"]}
    return {"update_available": False, "current": current_version}


@router.get("/releases")
async def list_releases(channel: Optional[str] = None):
    """List all releases."""
    results = _releases
    if channel:
        results = [r for r in results if r["channel"] == channel]
    return {"releases": results, "total": len(results)}
