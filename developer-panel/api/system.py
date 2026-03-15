"""Developer Panel - System and launch readiness API."""
from __future__ import annotations

from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import get_current_admin
from .config import get_settings
from .database import DevAdmin

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

router = APIRouter(prefix="/api/system", tags=["System"])
settings = get_settings()

license_client = None
license_client_error: str | None = None

_candidate_modules = [
    ROOT_DIR / "core" / "license-client" / "license_client.py",
    Path(__file__).resolve().parents[1] / "core" / "license-client" / "license_client.py",
]

for license_module_path in _candidate_modules:
    if not license_module_path.exists():
        continue
    try:
        _spec = importlib.util.spec_from_file_location("hs_license_client", license_module_path)
        if _spec is None or _spec.loader is None:
            raise RuntimeError(f"Unable to load license client module from {license_module_path}")
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_spec.name] = _module
        _spec.loader.exec_module(_module)
        license_client = _module.LicenseClient(
            _module.LicenseClientConfig(
                base_url=settings.LICENSE_SERVER_URL,
                validate_path=settings.LICENSE_VALIDATE_PATH,
                cache_file=Path(settings.LICENSE_CACHE_PATH),
                grace_hours=settings.LICENSE_GRACE_HOURS,
            )
        )
        license_client_error = None
        break
    except Exception as exc:
        license_client_error = str(exc)

if license_client is None and license_client_error is None:
    license_client_error = "License client module is not available in this runtime."


class LicenseCacheKeyUpdateRequest(BaseModel):
    license_key: str


def _is_default_secret(value: str, default_value: str) -> bool:
    return not value or value == default_value


def _add_check(results: list[dict], key: str, passed: bool, severity: str, message: str) -> None:
    results.append(
        {
            "key": key,
            "passed": passed,
            "severity": severity,
            "message": message,
        }
    )


def _container_runtime_probe() -> tuple[bool, str]:
    runtime = "docker" if shutil.which("docker") else ("podman" if shutil.which("podman") else "")
    if not runtime:
        return (False, "No container runtime found (docker/podman)")

    try:
        probe = subprocess.run([runtime, "info"], capture_output=True, text=True, timeout=5, check=False)
    except Exception as exc:
        return (False, f"{runtime} probe failed: {exc}")

    if probe.returncode == 0:
        return (True, f"{runtime} runtime is accessible")

    detail = (probe.stderr or probe.stdout or "runtime probe failed").strip()
    return (False, f"{runtime} runtime not accessible: {detail}")


def _build_preflight_report() -> dict:
    checks: list[dict] = []
    is_production = bool(settings.PRODUCTION_MODE and not settings.DEBUG)
    db_url = (settings.DATABASE_URL or "").strip().lower()

    _add_check(
        checks,
        "debug_mode_disabled",
        not settings.DEBUG,
        "critical",
        "Debug mode must be disabled before launch." if settings.DEBUG else "Debug mode is disabled.",
    )
    _add_check(
        checks,
        "production_mode_enabled",
        settings.PRODUCTION_MODE,
        "warning",
        "Set HSDEV_PRODUCTION_MODE=true for launch gating and stricter operational review."
        if not settings.PRODUCTION_MODE
        else "Production mode is enabled.",
    )
    _add_check(
        checks,
        "jwt_secret_hardened",
        not _is_default_secret(settings.JWT_SECRET, "dev-panel-secret-change-in-production") and len(settings.JWT_SECRET) >= 24,
        "critical",
        "Replace HSDEV_JWT_SECRET with a strong production secret (24+ chars)."
        if _is_default_secret(settings.JWT_SECRET, "dev-panel-secret-change-in-production") or len(settings.JWT_SECRET) < 24
        else "JWT secret is production-safe.",
    )
    _add_check(
        checks,
        "default_admin_password_rotated",
        settings.DEFAULT_ADMIN_PASSWORD != "Admin@123",
        "critical",
        "Rotate HSDEV_DEFAULT_ADMIN_PASSWORD and update seeded admin credentials before launch."
        if settings.DEFAULT_ADMIN_PASSWORD == "Admin@123"
        else "Default seeded admin password has been changed.",
    )
    _add_check(
        checks,
        "database_backend",
        "sqlite" not in db_url,
        "critical",
        "Move HSDEV_DATABASE_URL off SQLite to a production database backend."
        if "sqlite" in db_url
        else "Database backend is not SQLite.",
    )
    _add_check(
        checks,
        "whmcs_shared_secret_rotated",
        not _is_default_secret(settings.WHMCS_SHARED_SECRET, "change-this-whmcs-secret") and len(settings.WHMCS_SHARED_SECRET) >= 24,
        "critical",
        "Replace HSDEV_WHMCS_SHARED_SECRET with a strong secret (24+ chars)."
        if _is_default_secret(settings.WHMCS_SHARED_SECRET, "change-this-whmcs-secret") or len(settings.WHMCS_SHARED_SECRET) < 24
        else "WHMCS shared secret is production-safe.",
    )
    _add_check(
        checks,
        "whmcs_hmac_enabled",
        len((settings.WHMCS_HMAC_SECRET or "").strip()) >= 24,
        "critical",
        "Set HSDEV_WHMCS_HMAC_SECRET and configure matching WHMCS module secrets before launch."
        if len((settings.WHMCS_HMAC_SECRET or "").strip()) < 24
        else "WHMCS HMAC signing is enabled.",
    )
    _add_check(
        checks,
        "whmcs_ip_allowlist_set",
        bool((settings.WHMCS_ALLOWED_IPS or "").strip()),
        "warning",
        "Set HSDEV_WHMCS_ALLOWED_IPS to a comma-separated IP/CIDR allowlist for WHMCS callbacks."
        if not (settings.WHMCS_ALLOWED_IPS or "").strip()
        else "WHMCS source IP allowlist is configured.",
    )
    _add_check(
        checks,
        "license_api_key_present",
        bool((settings.LICENSE_API_KEY or "").strip()),
        "warning",
        "Set HSDEV_LICENSE_API_KEY if release workflows require license-server integration."
        if not (settings.LICENSE_API_KEY or "").strip()
        else "License server API key is configured.",
    )
    _add_check(
        checks,
        "license_cache_path_exists",
        Path(settings.LICENSE_CACHE_PATH).exists(),
        "warning",
        f"License cache path {settings.LICENSE_CACHE_PATH} does not exist yet."
        if not Path(settings.LICENSE_CACHE_PATH).exists()
        else f"License cache path {settings.LICENSE_CACHE_PATH} is present.",
    )
    _add_check(
        checks,
        "plugin_storage_path_exists",
        Path(settings.PLUGIN_STORAGE_PATH).exists(),
        "warning",
        f"Plugin storage path {settings.PLUGIN_STORAGE_PATH} does not exist on this host."
        if not Path(settings.PLUGIN_STORAGE_PATH).exists()
        else f"Plugin storage path {settings.PLUGIN_STORAGE_PATH} is present.",
    )
    runtime_ok, runtime_detail = _container_runtime_probe()
    _add_check(
        checks,
        "container_runtime_access",
        runtime_ok,
        "warning",
        runtime_detail,
    )

    blockers = [item for item in checks if not item["passed"] and item["severity"] == "critical"]
    warnings = [item for item in checks if not item["passed"] and item["severity"] == "warning"]
    return {
        "environment": "production" if is_production else "prelaunch",
        "ready": not blockers,
        "critical_failures": len(blockers),
        "warning_count": len(warnings),
        "checks": checks,
    }


@router.get("/preflight")
async def launch_preflight(_: DevAdmin = Depends(get_current_admin)):
    return {"success": True, "report": _build_preflight_report()}


@router.get("/license/runtime-status")
async def license_runtime_status(
    license_key: str | None = None,
    server_ip: str | None = None,
    fingerprint_hash: str | None = None,
    force_refresh: bool = False,
    _: DevAdmin = Depends(get_current_admin),
):
    if license_client is None:
        return {
            "success": False,
            "detail": "License runtime client is unavailable.",
            "reason": license_client_error,
        }
    return {
        "success": True,
        "data": license_client.validate(
            license_key=license_key,
            server_ip=server_ip,
            fingerprint_hash=fingerprint_hash,
            force_refresh=force_refresh,
        ),
    }


@router.post("/license/cache-key")
async def set_license_cache_key(
    body: LicenseCacheKeyUpdateRequest,
    _: DevAdmin = Depends(get_current_admin),
):
    if license_client is None:
        return {
            "success": False,
            "detail": "License runtime client is unavailable.",
            "reason": license_client_error,
        }
    updated = license_client.set_license_key(body.license_key)
    return {"success": True, "cache": updated}