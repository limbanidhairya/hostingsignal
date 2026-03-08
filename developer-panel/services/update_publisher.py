"""Update Publisher Service — Packages & pushes panel updates"""
import os
import hashlib
import shutil
import logging
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..api.database import PanelUpdate, ManagedServer
from ..api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UpdatePublisherService:
    """Handles panel update packaging, publishing, and distribution."""

    async def create_update(self, db: AsyncSession, version: str, channel: str = "stable",
                            changelog: str = "", file_path: str = None,
                            min_current_version: str = None, is_critical: bool = False) -> PanelUpdate:
        file_hash = None
        file_size = None
        download_url = None

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            file_size = os.path.getsize(file_path)

            dest_dir = os.path.join(settings.UPDATE_STORAGE_PATH, channel, version)
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, f"hostingsignal-{version}.tar.gz")
            shutil.copy2(file_path, dest_file)
            download_url = f"https://updates.hostingsignal.com/{channel}/{version}/hostingsignal-{version}.tar.gz"

            # Write version manifest
            manifest = {
                "version": version,
                "channel": channel,
                "hash": file_hash,
                "size": file_size,
                "url": download_url,
                "is_critical": is_critical,
                "min_current_version": min_current_version,
                "released_at": datetime.utcnow().isoformat(),
            }
            manifest_path = os.path.join(dest_dir, "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

        update = PanelUpdate(
            version=version, channel=channel, changelog=changelog,
            download_url=download_url, file_hash=file_hash,
            file_size=file_size, min_current_version=min_current_version,
            is_critical=is_critical,
        )
        db.add(update)
        await db.commit()
        await db.refresh(update)
        logger.info(f"Update created: v{version} ({channel})")
        return update

    async def publish_update(self, db: AsyncSession, update_id: str) -> PanelUpdate:
        result = await db.execute(select(PanelUpdate).where(PanelUpdate.id == update_id))
        upd = result.scalar_one_or_none()
        if not upd:
            raise ValueError("Update not found")
        upd.published = True
        upd.published_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Update published: v{upd.version}")
        return upd

    async def unpublish_update(self, db: AsyncSession, update_id: str) -> PanelUpdate:
        result = await db.execute(select(PanelUpdate).where(PanelUpdate.id == update_id))
        upd = result.scalar_one_or_none()
        if not upd:
            raise ValueError("Update not found")
        upd.published = False
        await db.commit()
        return upd

    async def get_latest_update(self, db: AsyncSession, channel: str = "stable",
                                current_version: str = None) -> Optional[dict]:
        stmt = (
            select(PanelUpdate)
            .where(PanelUpdate.channel == channel, PanelUpdate.published == True)
            .order_by(PanelUpdate.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        upd = result.scalar_one_or_none()
        if not upd:
            return None

        return {
            "version": upd.version,
            "channel": upd.channel,
            "changelog": upd.changelog,
            "download_url": upd.download_url,
            "file_hash": upd.file_hash,
            "file_size": upd.file_size,
            "is_critical": upd.is_critical,
            "published_at": upd.published_at.isoformat() if upd.published_at else None,
        }

    async def list_updates(self, db: AsyncSession, channel: str = None,
                           page: int = 1, per_page: int = 20) -> dict:
        stmt = select(PanelUpdate).order_by(PanelUpdate.created_at.desc())
        if channel:
            stmt = stmt.where(PanelUpdate.channel == channel)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        count_stmt = select(func.count(PanelUpdate.id))
        if channel:
            count_stmt = count_stmt.where(PanelUpdate.channel == channel)
        total = (await db.execute(count_stmt)).scalar()
        result = await db.execute(stmt)
        updates = result.scalars().all()

        return {
            "updates": [{
                "id": str(u.id), "version": u.version, "channel": u.channel,
                "changelog": u.changelog, "published": u.published,
                "is_critical": u.is_critical,
                "file_size": u.file_size,
                "published_at": u.published_at.isoformat() if u.published_at else None,
                "created_at": u.created_at.isoformat(),
            } for u in updates],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    async def get_update_adoption(self, db: AsyncSession) -> list:
        """Show how many servers are on each version."""
        result = await db.execute(
            select(
                ManagedServer.panel_version,
                func.count(ManagedServer.id).label("count")
            )
            .where(ManagedServer.panel_version.isnot(None))
            .group_by(ManagedServer.panel_version)
            .order_by(func.count(ManagedServer.id).desc())
        )
        return [{"version": row.panel_version, "servers": row.count} for row in result]


update_publisher = UpdatePublisherService()
