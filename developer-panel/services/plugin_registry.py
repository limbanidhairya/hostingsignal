"""Plugin Registry Service — Manages the plugin marketplace"""
import os
import json
import hashlib
import shutil
import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..api.database import PluginSubmission
from ..api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PluginRegistryService:
    """Handles plugin submission, review, publishing, and search."""

    ALLOWED_CATEGORIES = [
        "security", "backup", "email", "analytics",
        "optimization", "monitoring", "utility", "integration"
    ]

    async def submit_plugin(self, db: AsyncSession, name: str, slug: str, version: str,
                            author: str, description: str = "", category: str = "utility",
                            manifest: dict = None, file_path: str = None) -> PluginSubmission:
        file_hash = None
        file_size = None
        download_url = None

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            file_size = os.path.getsize(file_path)
            dest_dir = os.path.join(settings.PLUGIN_STORAGE_PATH, slug, version)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{slug}-{version}.tar.gz")
            shutil.copy2(file_path, dest_path)
            download_url = f"https://plugins.hostingsignal.com/download/{slug}/{version}/{slug}-{version}.tar.gz"

        plugin = PluginSubmission(
            name=name, slug=slug, version=version, author=author,
            description=description, category=category,
            manifest=manifest or {}, file_hash=file_hash,
            file_size=file_size, download_url=download_url,
            status="pending"
        )
        db.add(plugin)
        await db.commit()
        await db.refresh(plugin)
        logger.info(f"Plugin submitted: {slug} v{version} by {author}")
        return plugin

    async def approve_plugin(self, db: AsyncSession, plugin_id: str, notes: str = "") -> PluginSubmission:
        result = await db.execute(select(PluginSubmission).where(PluginSubmission.id == plugin_id))
        plugin = result.scalar_one_or_none()
        if not plugin:
            raise ValueError("Plugin not found")
        plugin.status = "approved"
        plugin.review_notes = notes
        await db.commit()
        logger.info(f"Plugin approved: {plugin.slug}")
        return plugin

    async def publish_plugin(self, db: AsyncSession, plugin_id: str) -> PluginSubmission:
        result = await db.execute(select(PluginSubmission).where(PluginSubmission.id == plugin_id))
        plugin = result.scalar_one_or_none()
        if not plugin:
            raise ValueError("Plugin not found")
        if plugin.status != "approved":
            raise ValueError("Plugin must be approved before publishing")
        plugin.status = "published"
        await db.commit()
        logger.info(f"Plugin published: {plugin.slug}")
        return plugin

    async def reject_plugin(self, db: AsyncSession, plugin_id: str, reason: str) -> PluginSubmission:
        result = await db.execute(select(PluginSubmission).where(PluginSubmission.id == plugin_id))
        plugin = result.scalar_one_or_none()
        if not plugin:
            raise ValueError("Plugin not found")
        plugin.status = "rejected"
        plugin.review_notes = reason
        await db.commit()
        return plugin

    async def search_plugins(self, db: AsyncSession, query: str = "", category: str = None,
                             status: str = "published", page: int = 1, per_page: int = 20) -> dict:
        stmt = select(PluginSubmission).where(PluginSubmission.status == status)
        if query:
            stmt = stmt.where(PluginSubmission.name.ilike(f"%{query}%"))
        if category:
            stmt = stmt.where(PluginSubmission.category == category)
        stmt = stmt.order_by(PluginSubmission.downloads.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        count_stmt = select(func.count(PluginSubmission.id)).where(PluginSubmission.status == status)
        total = (await db.execute(count_stmt)).scalar()
        result = await db.execute(stmt)
        plugins = result.scalars().all()

        return {
            "plugins": plugins,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    async def increment_downloads(self, db: AsyncSession, slug: str):
        result = await db.execute(
            select(PluginSubmission).where(PluginSubmission.slug == slug, PluginSubmission.status == "published")
        )
        plugin = result.scalar_one_or_none()
        if plugin:
            plugin.downloads += 1
            await db.commit()

    async def get_marketplace_stats(self, db: AsyncSession) -> dict:
        total = (await db.execute(select(func.count(PluginSubmission.id)))).scalar()
        published = (await db.execute(
            select(func.count(PluginSubmission.id)).where(PluginSubmission.status == "published")
        )).scalar()
        pending = (await db.execute(
            select(func.count(PluginSubmission.id)).where(PluginSubmission.status == "pending")
        )).scalar()
        total_downloads = (await db.execute(
            select(func.sum(PluginSubmission.downloads))
        )).scalar() or 0

        return {
            "total_plugins": total,
            "published": published,
            "pending_review": pending,
            "total_downloads": total_downloads,
        }


plugin_registry = PluginRegistryService()
