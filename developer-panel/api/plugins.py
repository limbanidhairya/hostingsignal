"""Developer Panel — Plugin Marketplace API"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import secrets
from datetime import datetime, timezone

router = APIRouter(prefix="/api/plugins", tags=["Plugin Marketplace"])

_plugins: dict = {}

CATEGORIES = ["security", "backup", "email", "analytics", "optimization", "monitoring", "utility"]


class PublishPluginRequest(BaseModel):
    name: str
    version: str
    description: str
    author: str
    category: str
    min_panel_version: str = "1.0.0"
    price: float = 0.0  # 0 = free


@router.get("/marketplace")
async def marketplace(category: Optional[str] = None, search: Optional[str] = None):
    """Browse plugin marketplace."""
    results = list(_plugins.values())
    if category:
        results = [p for p in results if p["category"] == category]
    if search:
        results = [p for p in results if search.lower() in p["name"].lower() or search.lower() in p["description"].lower()]
    return {"plugins": results, "total": len(results), "categories": CATEGORIES}


@router.post("/publish")
async def publish_plugin(body: PublishPluginRequest):
    """Publish a new plugin to the marketplace."""
    plugin_id = f"plugin_{secrets.token_hex(8)}"
    plugin = {
        "id": plugin_id,
        "name": body.name,
        "version": body.version,
        "description": body.description,
        "author": body.author,
        "category": body.category,
        "min_panel_version": body.min_panel_version,
        "price": body.price,
        "downloads": 0,
        "rating": 0.0,
        "status": "pending_review",
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    _plugins[plugin_id] = plugin
    return {"status": "success", "plugin_id": plugin_id, "message": "Plugin submitted for review"}


@router.post("/{plugin_id}/approve")
async def approve_plugin(plugin_id: str):
    """Approve a plugin for the marketplace."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    _plugins[plugin_id]["status"] = "approved"
    return {"status": "success", "message": "Plugin approved"}


@router.delete("/{plugin_id}")
async def remove_plugin(plugin_id: str):
    """Remove a plugin from the marketplace."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    del _plugins[plugin_id]
    return {"status": "success", "message": "Plugin removed"}


@router.get("/stats")
async def plugin_stats():
    """Plugin marketplace statistics."""
    total = len(_plugins)
    approved = sum(1 for p in _plugins.values() if p["status"] == "approved")
    pending = sum(1 for p in _plugins.values() if p["status"] == "pending_review")
    by_category = {}
    for p in _plugins.values():
        by_category[p["category"]] = by_category.get(p["category"], 0) + 1
    return {"total": total, "approved": approved, "pending": pending, "by_category": by_category}
