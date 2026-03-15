"""Developer Panel - WHMCS Integration API."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import get_current_admin
from .config import get_settings
from .database import DevAdmin
from .plugins import BUILTIN_PLUGINS, PLAN_ORDER

router = APIRouter(prefix="/api/whmcs", tags=["WHMCS Integration"])
settings = get_settings()
QUEUE_DIR = Path("/var/hspanel/queue")
MAPPINGS_FILE = Path("/var/hspanel/userdata/whmcs_product_mappings.json")
WHMCS_AUDIT_LOG_FILE = Path("/var/hspanel/logs/whmcs_audit.log")
NONCE_CACHE: dict[str, float] = {}


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


def _audit_event(action: str, success: bool, details: dict) -> None:
    try:
        WHMCS_AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "success": success,
            "details": details,
        }
        with WHMCS_AUDIT_LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except Exception:
        # Audit logging should never break provisioning flow.
        return


def _evict_expired_nonces(now: float) -> None:
    expired = [nonce for nonce, expires_at in NONCE_CACHE.items() if expires_at <= now]
    for nonce in expired:
        NONCE_CACHE.pop(nonce, None)


def _reject_whmcs_request(status_code: int, detail: str, client_ip: str, reason: str) -> None:
    _audit_event(
        "whmcs_auth_rejected",
        False,
        {
            "client_ip": client_ip,
            "reason": reason,
            "detail": detail,
        },
    )
    raise HTTPException(status_code=status_code, detail=detail)


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        first = forwarded_for.split(",", 1)[0].strip()
        if first:
            return first
    return (request.client.host if request.client else "") or ""


def _ip_allowed_by_policy(client_ip: str) -> bool:
    # Always allow local loopback requests for local panel runtime and testing.
    if client_ip in {"127.0.0.1", "::1", "localhost"}:
        return True

    raw = (settings.WHMCS_ALLOWED_IPS or "").strip()
    if not raw:
        return True

    candidates = [x.strip() for x in raw.split(",") if x.strip()]
    if not candidates:
        return True

    try:
        parsed_ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    any_valid_rule = False
    for rule in candidates:
        try:
            if "/" in rule:
                network = ipaddress.ip_network(rule, strict=False)
                any_valid_rule = True
                if parsed_ip in network:
                    return True
            else:
                listed_ip = ipaddress.ip_address(rule)
                any_valid_rule = True
                if parsed_ip == listed_ip:
                    return True
        except ValueError:
            continue

    return not any_valid_rule


def _query_recent_audit_entries(limit: int, offset: int, action: str | None, success: bool | None) -> tuple[list[dict], int]:
    if not WHMCS_AUDIT_LOG_FILE.exists():
        return ([], 0)

    try:
        lines = WHMCS_AUDIT_LOG_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ([], 0)

    matched_entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if not isinstance(item, dict):
            continue
        if action and str(item.get("action", "")) != action:
            continue
        if success is not None and bool(item.get("success")) is not success:
            continue
        matched_entries.append(item)

    total = len(matched_entries)
    if offset >= total:
        return ([], total)

    return (matched_entries[offset : offset + limit], total)


async def _authorize_whmcs(
    request: Request,
    x_hs_whmcs_token: str = Header(default=""),
    x_hs_whmcs_timestamp: str = Header(default=""),
    x_hs_whmcs_signature: str = Header(default=""),
    x_hs_whmcs_nonce: str = Header(default=""),
):
    client_ip = _extract_client_ip(request)
    if not _ip_allowed_by_policy(client_ip):
        _reject_whmcs_request(403, "Source IP is not allowed", client_ip, "ip_allowlist")

    if not settings.WHMCS_SHARED_SECRET:
        raise HTTPException(status_code=500, detail="WHMCS shared secret is not configured")
    if x_hs_whmcs_token != settings.WHMCS_SHARED_SECRET:
        _reject_whmcs_request(401, "Unauthorized WHMCS token", client_ip, "shared_token")

    if settings.WHMCS_HMAC_SECRET:
        if not x_hs_whmcs_timestamp or not x_hs_whmcs_signature:
            _reject_whmcs_request(401, "Missing HMAC headers", client_ip, "missing_hmac_headers")

        try:
            request_timestamp = int(x_hs_whmcs_timestamp)
        except ValueError:
            _reject_whmcs_request(401, "Invalid timestamp header", client_ip, "invalid_timestamp")

        now = int(time.time())
        if abs(now - request_timestamp) > settings.WHMCS_HMAC_MAX_SKEW_SECONDS:
            _reject_whmcs_request(401, "Stale WHMCS request", client_ip, "stale_request")

        body = await request.body()
        signing_payload = x_hs_whmcs_timestamp.encode("utf-8") + b"." + body
        expected_signature = hmac.new(
            settings.WHMCS_HMAC_SECRET.encode("utf-8"),
            signing_payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_hs_whmcs_signature):
            _reject_whmcs_request(401, "Invalid WHMCS signature", client_ip, "invalid_signature")

        if x_hs_whmcs_nonce:
            now_float = float(now)
            _evict_expired_nonces(now_float)
            if x_hs_whmcs_nonce in NONCE_CACHE:
                _reject_whmcs_request(401, "Replay detected", client_ip, "replay_detected")
            NONCE_CACHE[x_hs_whmcs_nonce] = now_float + float(settings.WHMCS_NONCE_TTL_SECONDS)

    return True


@router.get("/audit/recent")
async def get_recent_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None),
    success: Optional[bool] = Query(default=None),
    _: DevAdmin = Depends(get_current_admin),
):
    entries, total = _query_recent_audit_entries(limit=limit, offset=offset, action=action, success=success)
    has_more = (offset + len(entries)) < total
    return {
        "success": True,
        "limit": limit,
        "offset": offset,
        "total": total,
        "returned": len(entries),
        "has_more": has_more,
        "filters": {"action": action, "success": success},
        "entries": entries,
    }


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
    _audit_event(
        "product_mapping_upsert",
        True,
        {"product_id": body.product_id, "plan": plan, "plugin_count": len(body.include_plugins)},
    )
    return {"success": True, "product_id": body.product_id, "mapping": mappings[str(body.product_id)]}


@router.post("/product-mappings/delete")
async def delete_product_mapping(body: ProductResolveRequest, _: bool = Depends(_authorize_whmcs)):
    mappings = _load_product_mappings()
    removed = mappings.pop(str(body.product_id), None)
    _save_product_mappings(mappings)
    _audit_event("product_mapping_delete", True, {"product_id": body.product_id, "deleted": removed is not None})
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
    _audit_event(
        "provision_create_account",
        True,
        {
            "service_id": body.service_id,
            "client_id": body.client_id,
            "domain": body.domain,
            "product_id": body.whmcs_product_id,
            "plan": plan,
            "job_id": job["job_id"],
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
    _audit_event(
        "provision_suspend_account",
        True,
        {"service_id": body.service_id, "domain": body.domain, "job_id": job["job_id"]},
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
    _audit_event(
        "provision_unsuspend_account",
        True,
        {"service_id": body.service_id, "domain": body.domain, "job_id": job["job_id"]},
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
    _audit_event(
        "provision_terminate_account",
        True,
        {"service_id": body.service_id, "domain": body.domain, "job_id": job["job_id"]},
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
    _audit_event("license_validate", True, {"domain": body.domain})
    return {
        "success": True,
        "license_key": body.license_key,
        "domain": body.domain,
        "status": "valid",
        "message": "License validation placeholder. Wire this to license-server validate API for production.",
    }
