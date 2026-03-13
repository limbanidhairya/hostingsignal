"""Developer Panel — Plugin Marketplace API (service-backed)."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from services.plugin_registry import plugin_registry

router = APIRouter(prefix="/api/plugins", tags=["Plugin Marketplace"])

PLAN_ORDER = {
    "starter": 1,
    "professional": 2,
    "business": 3,
    "enterprise": 4,
}

BUILTIN_PLUGINS = [
    {
        "id": "vulnerability-scanner",
        "name": "Open Source Vulnerability Scanner",
        "slug": "vulnerability-scanner",
        "version": "1.0.0",
        "category": "security",
        "status": "published",
        "author": "HostingSignal",
        "description": "Nuclei/OWASP-based scanning workflows for websites and apps.",
        "required_plan": "professional",
        "admin_override_allowed": True,
        "manifest": {
            "open_source_stack": ["nuclei", "owasp-zap"],
            "requires_agent": True,
        },
    },
    {
        "id": "wordpress-manager",
        "name": "WordPress Manager",
        "slug": "wordpress-manager",
        "version": "1.0.0",
        "category": "integration",
        "status": "published",
        "author": "HostingSignal",
        "description": "Manage WP installs, updates, and hardening from one panel.",
        "required_plan": "professional",
        "admin_override_allowed": True,
        "manifest": {
            "features": ["one-click-install", "core-plugin-update", "security-hardening"],
        },
    },
    {
        "id": "node-app-manager",
        "name": "Node App Manager",
        "slug": "node-app-manager",
        "version": "1.0.0",
        "category": "devops",
        "status": "published",
        "author": "HostingSignal",
        "description": "Deploy and supervise Node.js applications with process control.",
        "required_plan": "starter",
        "admin_override_allowed": True,
        "manifest": {
            "runtime": "nodejs",
            "supports": ["pm2", "systemd"],
        },
    },
    {
        "id": "react-app-manager",
        "name": "React App Manager",
        "slug": "react-app-manager",
        "version": "1.0.0",
        "category": "devops",
        "status": "published",
        "author": "HostingSignal",
        "description": "Build, publish, and monitor React/Next frontend applications.",
        "required_plan": "starter",
        "admin_override_allowed": True,
        "manifest": {
            "runtime": "nodejs",
            "frameworks": ["react", "nextjs"],
        },
    },
    {
        "id": "python-app-manager",
        "name": "Python App Manager",
        "slug": "python-app-manager",
        "version": "1.0.0",
        "category": "devops",
        "status": "published",
        "author": "HostingSignal",
        "description": "Manage Python web apps with virtualenv and service orchestration.",
        "required_plan": "starter",
        "admin_override_allowed": True,
        "manifest": {
            "runtime": "python",
            "supports": ["gunicorn", "uvicorn"],
        },
    },
    {
        "id": "docker-service-manager",
        "name": "Docker Service Manager",
        "slug": "docker-service-manager",
        "version": "1.0.0",
        "category": "devops",
        "status": "published",
        "author": "HostingSignal",
        "description": "Run and manage containerized workloads and compose stacks.",
        "required_plan": "professional",
        "admin_override_allowed": True,
        "manifest": {
            "runtime": "docker",
            "supports": ["compose", "registry-pull", "service-health"],
        },
    },
    {
        "id": "whmcs-addon",
        "name": "WHMCS Billing Integration Addon",
        "slug": "whmcs-addon",
        "version": "1.0.0",
        "category": "integration",
        "status": "published",
        "author": "HostingSignal",
        "description": "Provision and sync HostingSignal packages with WHMCS products.",
        "required_plan": "professional",
        "admin_override_allowed": True,
        "manifest": {
            "addon_type": "whmcs",
            "hooks": ["AfterModuleCreate", "AfterModuleTerminate", "DailyCronJob"],
            "api": ["ValidateLicense", "SyncPackage"],
        },
    },
]


class PublishPluginRequest(BaseModel):
    name: str
    version: str
    description: str
    author: str
    category: str
    min_panel_version: str = "1.0.0"
    price: float = 0.0


class PackageCreateRequest(BaseModel):
    package_name: str
    plan: str
    include_plugins: list[str] = []
    admin_override: bool = False


def _plan_allows(required_plan: str, selected_plan: str) -> bool:
    required = PLAN_ORDER.get((required_plan or "starter").lower(), 1)
    selected = PLAN_ORDER.get((selected_plan or "starter").lower(), 1)
    return selected >= required


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


@router.get("/catalog")
async def plugin_catalog() -> dict:
    """Return built-in plugin catalog used for package composition."""
    return {
        "plugins": BUILTIN_PLUGINS,
        "plans": sorted(PLAN_ORDER.keys(), key=lambda p: PLAN_ORDER[p]),
        "paid_plans": ["starter", "professional", "business", "enterprise"],
    }


@router.post("/packages/create")
async def create_package(body: PackageCreateRequest) -> dict:
    """Compute package plugin availability with plan limits and admin overrides."""
    if body.plan.lower() not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Unknown plan. Use starter/professional/business/enterprise")

    selected = set(body.include_plugins)
    available = []
    blocked = []

    for plugin in BUILTIN_PLUGINS:
        requested = plugin["slug"] in selected or plugin["id"] in selected
        allowed = _plan_allows(plugin["required_plan"], body.plan)
        override_used = False
        if not allowed and requested and body.admin_override and plugin.get("admin_override_allowed"):
            allowed = True
            override_used = True

        item = {
            "id": plugin["id"],
            "name": plugin["name"],
            "slug": plugin["slug"],
            "required_plan": plugin["required_plan"],
            "enabled": requested and allowed,
            "override_used": override_used,
        }

        if requested and allowed:
            available.append(item)
        elif requested and not allowed:
            item["reason"] = f"Requires {plugin['required_plan']} plan or admin override"
            blocked.append(item)

    return {
        "package": {
            "name": body.package_name,
            "plan": body.plan.lower(),
            "admin_override": body.admin_override,
            "enabled_plugins": available,
            "blocked_plugins": blocked,
        },
        "whmcs_addon_available": any(p["slug"] == "whmcs-addon" and p["enabled"] for p in available),
        "message": "Package evaluated. Persist this payload in your billing/package service.",
    }


@router.get("/addons/whmcs")
async def whmcs_addon_descriptor() -> dict:
    """Return WHMCS addon integration descriptor for billing automation wiring."""
    addon = next((p for p in BUILTIN_PLUGINS if p["slug"] == "whmcs-addon"), None)
    return {
        "addon": addon,
        "integration": {
            "name": "hostingsignal_whmcs",
            "module_type": "server",
            "required_config": ["whmcs_url", "api_identifier", "api_secret", "license_server_url"],
            "provisioning_actions": [
                "CreateAccount -> create HostingSignal package/user",
                "SuspendAccount -> suspend package services",
                "UnsuspendAccount -> restore package services",
                "TerminateAccount -> delete package resources",
            ],
        },
    }


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
