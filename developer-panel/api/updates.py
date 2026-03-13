"""Developer Panel — Update Push API (service-backed)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from services.update_publisher import update_publisher

router = APIRouter(prefix="/api/updates", tags=["Updates"])


class CreateReleaseRequest(BaseModel):
    version: str
    channel: str = "stable"  # stable | beta | dev
    changelog: str = ""
    min_current_version: Optional[str] = None
    archive_path: Optional[str] = None
    is_critical: bool = False


class PublishReleaseRequest(BaseModel):
    update_id: str


@router.post("/release")
async def create_release(body: CreateReleaseRequest, db: AsyncSession = Depends(get_db)):
    """Create a release artifact record in update service."""
    try:
        upd = await update_publisher.create_update(
            db=db,
            version=body.version,
            channel=body.channel,
            changelog=body.changelog,
            file_path=body.archive_path,
            min_current_version=body.min_current_version,
            is_critical=body.is_critical,
        )
        return {
            "success": True,
            "update": {
                "id": str(upd.id),
                "version": upd.version,
                "channel": upd.channel,
                "download_url": upd.download_url,
                "published": upd.published,
                "is_critical": upd.is_critical,
            },
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/release/publish")
async def publish_release(body: PublishReleaseRequest, db: AsyncSession = Depends(get_db)):
    try:
        upd = await update_publisher.publish_update(db, body.update_id)
        return {
            "success": True,
            "update": {
                "id": str(upd.id),
                "version": upd.version,
                "channel": upd.channel,
                "published": upd.published,
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/latest/{channel}")
async def latest_release(channel: str = "stable", db: AsyncSession = Depends(get_db)):
    """Get latest published version for a channel."""
    latest = await update_publisher.get_latest_update(db=db, channel=channel)
    if latest is None:
        return {"version": "1.0.0", "channel": channel, "message": "No releases found"}
    return latest


@router.get("/check")
async def check_update(current_version: str, channel: str = "stable", db: AsyncSession = Depends(get_db)):
    """Check if update is available."""
    latest = await update_publisher.get_latest_update(db=db, channel=channel, current_version=current_version)
    if latest and latest.get("version", "") > current_version:
        return {
            "update_available": True,
            "latest": latest.get("version"),
            "download_url": latest.get("download_url"),
            "is_critical": latest.get("is_critical", False),
        }
    return {"update_available": False, "current": current_version}


@router.get("/releases")
async def list_releases(
    channel: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List release records from update service."""
    return await update_publisher.list_updates(db=db, channel=channel, page=page, per_page=per_page)
