"""Developer Panel — Plugin Marketplace API (service-backed)."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from ..services.plugin_registry import plugin_registry

router = APIRouter(prefix="/api/plugins", tags=["Plugin Marketplace"])


class PublishPluginRequest(BaseModel):
    name: str
    version: str
    description: str
    author: str
    category: str
    min_panel_version: str = "1.0.0"
    price: float = 0.0


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _plugin_to_dict(plugin) -> dict:
    return {
        "id": str(plugin.id),
        "name": plugin.name,
        "slug": plugin.slug,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "category": plugin.category,
        "status": plugin.status,
        "downloads": plugin.downloads,
        "rating": plugin.rating,
        "download_url": plugin.download_url,
        "created_at": plugin.created_at.isoformat() if plugin.created_at else None,
    }


@router.get("/marketplace")
async def marketplace(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        payload = await plugin_registry.search_plugins(
            db=db,
            query=search or "",
            category=category,
            status="published",
            page=page,
            per_page=per_page,
        )
        payload["plugins"] = [_plugin_to_dict(p) for p in payload["plugins"]]
        payload["categories"] = plugin_registry.ALLOWED_CATEGORIES
        return payload
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/publish")
async def publish_plugin(body: PublishPluginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        plugin = await plugin_registry.submit_plugin(
            db=db,
            name=body.name,
            slug=_slugify(body.name),
            version=body.version,
            author=body.author,
            description=body.description,
            category=body.category,
            manifest={
                "min_panel_version": body.min_panel_version,
                "price": body.price,
            },
            file_path=None,
        )
        return {"success": True, "plugin": _plugin_to_dict(plugin), "message": "Plugin submitted for review"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{plugin_id}/approve")
async def approve_plugin(plugin_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        plugin = await plugin_registry.approve_plugin(db, plugin_id)
        return {"success": True, "plugin": _plugin_to_dict(plugin)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{plugin_id}/publish")
async def publish_plugin_live(plugin_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        plugin = await plugin_registry.publish_plugin(db, plugin_id)
        return {"success": True, "plugin": _plugin_to_dict(plugin)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{plugin_id}/reject")
async def reject_plugin(plugin_id: str, reason: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        plugin = await plugin_registry.reject_plugin(db, plugin_id, reason)
        return {"success": True, "plugin": _plugin_to_dict(plugin)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/stats")
async def plugin_stats(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return await plugin_registry.get_marketplace_stats(db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
