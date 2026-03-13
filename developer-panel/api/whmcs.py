"""Developer Panel - WHMCS Integration API."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .config import get_settings
from .plugins import BUILTIN_PLUGINS, PLAN_ORDER

router = APIRouter(prefix="/api/whmcs", tags=["WHMCS Integration"])
settings = get_settings()
QUEUE_DIR = Path("/var/hspanel/queue")
MAPPINGS_FILE = Path("/var/hspanel/userdata/whmcs_product_mappings.json")


class PackageSyncRequest(BaseModel):
    package_name: str
    plan: str
    include_plugins: list[str] = Field(default_factory=list)
    admin_override: bool = False
    whmcs_product_id: Optional[int] = None


class ProvisionRequest(BaseModel):
    service_id: int
    client_id: int
    domain: str
    package_name: str
    plan: str
    include_plugins: list[str] = Field(default_factory=list)
    admin_override: bool = False
    whmcs_product_id: Optional[int] = None


class ProductMappingRequest(BaseModel):
    product_id: int
    package_name: str
    plan: str
    include_plugins: list[str] = Field(default_factory=list)
    admin_override: bool = False


class ProductResolveRequest(BaseModel):
    product_id: int
    fallback_plan: str = "starter"
    fallback_package_name: str = "whmcs-package"
    fallback_plugins: list[str] = Field(default_factory=list)
    fallback_admin_override: bool = False


class ServiceLifecycleRequest(BaseModel):
    service_id: int
    domain: Optional[str] = None
    reason: Optional[str] = None


class ValidateLicenseRequest(BaseModel):
    license_key: str
    domain: str


def _plan_allows(required_plan: str, selected_plan: str) -> bool:
    required = PLAN_ORDER.get((required_plan or "starter").lower(), 1)
    selected = PLAN_ORDER.get((selected_plan or "starter").lower(), 1)
    return selected >= required


def _evaluate_plugins(plan: str, requested: list[str], admin_override: bool) -> dict:
    selected = {x.lower() for x in requested}
    enabled_plugins = []
    blocked_plugins = []

    for plugin in BUILTIN_PLUGINS:
        slug = plugin["slug"]
        required_plan = plugin["required_plan"]
        requested_for_package = slug in selected or plugin["id"] in selected
        if not requested_for_package:
            continue

        allowed = _plan_allows(required_plan, plan)
        override_used = False
        if not allowed and admin_override and plugin.get("admin_override_allowed"):
            allowed = True
            override_used = True

        entry = {
            "id": plugin["id"],
            "slug": slug,
            "name": plugin["name"],
            "required_plan": required_plan,
            "enabled": allowed,
            "override_used": override_used,
        }

        if allowed:
            enabled_plugins.append(entry)
        else:
            entry["reason"] = f"Requires {required_plan} plan or admin override"
            blocked_plugins.append(entry)

    return {
        "enabled_plugins": enabled_plugins,
        "blocked_plugins": blocked_plugins,
        "whmcs_addon_available": any(p["slug"] == "whmcs-addon" for p in enabled_plugins),
    }


def _enqueue_job(action: str, payload: dict) -> dict:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid.uuid4())
    job_payload = {
        "id": job_id,
        "type": action,
        **payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    job_path = QUEUE_DIR / f"{job_id}.json"
    job_path.write_text(json.dumps(job_payload, indent=2), encoding="utf-8")
    return {"job_id": job_id, "job_file": str(job_path), "payload": job_payload}


def _load_product_mappings() -> dict:
    if not MAPPINGS_FILE.exists():
        return {}
    try:
        data = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_product_mappings(data: dict) -> None:
    MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAPPINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _resolve_package_config(
    product_id: Optional[int],
    fallback_plan: str,
    fallback_package_name: str,
    fallback_plugins: list[str],
    fallback_admin_override: bool,
) -> dict:
    mappings = _load_product_mappings()
    key = str(product_id) if product_id is not None else ""
    mapped = mappings.get(key)
    if not isinstance(mapped, dict):
        return {
            "source": "fallback",
            "plan": fallback_plan,
            "package_name": fallback_package_name,
            "include_plugins": fallback_plugins,
            "admin_override": fallback_admin_override,
        }
    return {
        "source": "mapping",
        "plan": str(mapped.get("plan", fallback_plan)),
        "package_name": str(mapped.get("package_name", fallback_package_name)),
        "include_plugins": list(mapped.get("include_plugins", fallback_plugins) or []),
        "admin_override": bool(mapped.get("admin_override", fallback_admin_override)),
    }


def _authorize_whmcs(x_hs_whmcs_token: str = Header(default="")):
    if not settings.WHMCS_SHARED_SECRET:
        raise HTTPException(status_code=500, detail="WHMCS shared secret is not configured")
    if x_hs_whmcs_token != settings.WHMCS_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized WHMCS token")
    return True


@router.get("/health")
async def whmcs_health(_: bool = Depends(_authorize_whmcs)):
    return {
        "status": "ok",
        "service": "whmcs-integration",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/product-mappings")
async def list_product_mappings(_: bool = Depends(_authorize_whmcs)):
    return {"success": True, "mappings": _load_product_mappings()}


@router.post("/product-mappings/upsert")
async def upsert_product_mapping(body: ProductMappingRequest, _: bool = Depends(_authorize_whmcs)):
    plan = body.plan.lower()
    if plan not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Unknown plan. Use starter/professional/business/enterprise")

    mappings = _load_product_mappings()
    mappings[str(body.product_id)] = {
        "package_name": body.package_name,
        "plan": plan,
        "include_plugins": body.include_plugins,
        "admin_override": body.admin_override,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_product_mappings(mappings)
    return {"success": True, "product_id": body.product_id, "mapping": mappings[str(body.product_id)]}


@router.post("/product-mappings/delete")
async def delete_product_mapping(body: ProductResolveRequest, _: bool = Depends(_authorize_whmcs)):
    mappings = _load_product_mappings()
    removed = mappings.pop(str(body.product_id), None)
    _save_product_mappings(mappings)
    return {"success": True, "product_id": body.product_id, "deleted": removed is not None}


@router.post("/product-mappings/resolve")
async def resolve_product_mapping(body: ProductResolveRequest, _: bool = Depends(_authorize_whmcs)):
    resolved = _resolve_package_config(
        body.product_id,
        body.fallback_plan,
        body.fallback_package_name,
        body.fallback_plugins,
        body.fallback_admin_override,
    )
    return {"success": True, "product_id": body.product_id, "resolved": resolved}


@router.post("/package/sync")
async def package_sync(body: PackageSyncRequest, _: bool = Depends(_authorize_whmcs)):
    resolved = _resolve_package_config(
        body.whmcs_product_id,
        body.plan.lower(),
        body.package_name,
        body.include_plugins,
        body.admin_override,
    )
    plan = str(resolved["plan"]).lower()
    if plan not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Unknown plan. Use starter/professional/business/enterprise")

    evaluation = _evaluate_plugins(plan, resolved["include_plugins"], resolved["admin_override"])
    return {
        "success": True,
        "whmcs_product_id": body.whmcs_product_id,
        "config_source": resolved["source"],
        "package": {
            "name": resolved["package_name"],
            "plan": plan,
            "admin_override": resolved["admin_override"],
            "enabled_plugins": evaluation["enabled_plugins"],
            "blocked_plugins": evaluation["blocked_plugins"],
        },
        "whmcs_addon_available": evaluation["whmcs_addon_available"],
    }


@router.post("/provision/create-account")
async def create_account(body: ProvisionRequest, _: bool = Depends(_authorize_whmcs)):
    resolved = _resolve_package_config(
        body.whmcs_product_id,
        body.plan.lower(),
        body.package_name,
        body.include_plugins,
        body.admin_override,
    )
    plan = str(resolved["plan"]).lower()
    if plan not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Unknown plan")

    evaluation = _evaluate_plugins(plan, resolved["include_plugins"], resolved["admin_override"])
    job = _enqueue_job(
        "whmcs_create_account",
        {
            "service_id": body.service_id,
            "client_id": body.client_id,
            "domain": body.domain,
            "package_name": resolved["package_name"],
            "plan": plan,
        },
    )
    return {
        "success": True,
        "action": "create-account",
        "service_id": body.service_id,
        "client_id": body.client_id,
        "whmcs_product_id": body.whmcs_product_id,
        "config_source": resolved["source"],
        "domain": body.domain,
        "package": resolved["package_name"],
        "plan": plan,
        "plugins": evaluation,
        "queued_job": {"id": job["job_id"], "path": job["job_file"]},
        "message": "Provisioning queued for hs-taskd execution.",
    }


@router.post("/provision/suspend-account")
async def suspend_account(body: ServiceLifecycleRequest, _: bool = Depends(_authorize_whmcs)):
    job = _enqueue_job(
        "whmcs_suspend_account",
        {
            "service_id": body.service_id,
            "domain": body.domain,
            "reason": body.reason or "Suspended by WHMCS",
        },
    )
    return {
        "success": True,
        "action": "suspend-account",
        "service_id": body.service_id,
        "domain": body.domain,
        "reason": body.reason or "Suspended by WHMCS",
        "queued_job": {"id": job["job_id"], "path": job["job_file"]},
    }


@router.post("/provision/unsuspend-account")
async def unsuspend_account(body: ServiceLifecycleRequest, _: bool = Depends(_authorize_whmcs)):
    job = _enqueue_job(
        "whmcs_unsuspend_account",
        {
            "service_id": body.service_id,
            "domain": body.domain,
        },
    )
    return {
        "success": True,
        "action": "unsuspend-account",
        "service_id": body.service_id,
        "domain": body.domain,
        "queued_job": {"id": job["job_id"], "path": job["job_file"]},
    }


@router.post("/provision/terminate-account")
async def terminate_account(body: ServiceLifecycleRequest, _: bool = Depends(_authorize_whmcs)):
    job = _enqueue_job(
        "whmcs_terminate_account",
        {
            "service_id": body.service_id,
            "domain": body.domain,
            "reason": body.reason or "Terminated by WHMCS",
        },
    )
    return {
        "success": True,
        "action": "terminate-account",
        "service_id": body.service_id,
        "domain": body.domain,
        "reason": body.reason or "Terminated by WHMCS",
        "queued_job": {"id": job["job_id"], "path": job["job_file"]},
    }


@router.post("/license/validate")
async def validate_license(body: ValidateLicenseRequest, _: bool = Depends(_authorize_whmcs)):
    return {
        "success": True,
        "license_key": body.license_key,
        "domain": body.domain,
        "status": "valid",
        "message": "License validation placeholder. Wire this to license-server validate API for production.",
    }
