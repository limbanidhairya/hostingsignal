"""Setup Wizard API — First-run configuration wizard"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import json

router = APIRouter(prefix="/api/setup", tags=["Setup Wizard"])

SETUP_CONFIG_PATH = "/etc/hostingsignal/setup_complete.json"


def is_setup_complete() -> bool:
    return os.path.exists(SETUP_CONFIG_PATH)


@router.get("/status")
async def setup_status():
    """Check if initial setup has been completed."""
    return {
        "setup_complete": is_setup_complete(),
        "steps": [
            {"id": "admin", "label": "Create Admin Account", "completed": is_setup_complete()},
            {"id": "license", "label": "Activate License", "completed": is_setup_complete()},
            {"id": "webserver", "label": "Configure Web Server", "completed": is_setup_complete()},
            {"id": "dns", "label": "Setup DNS (optional)", "completed": False},
            {"id": "ssl", "label": "SSL Certificates", "completed": False},
        ],
    }


@router.post("/complete")
async def complete_setup(request: Request):
    """Mark the setup wizard as complete."""
    data = await request.json()
    os.makedirs(os.path.dirname(SETUP_CONFIG_PATH), exist_ok=True)
    with open(SETUP_CONFIG_PATH, "w") as f:
        json.dump({
            "completed_at": __import__("datetime").datetime.utcnow().isoformat(),
            "admin_email": data.get("admin_email", "admin@hostingsignal.com"),
            "web_server": data.get("web_server", "openlitespeed"),
        }, f, indent=2)
    return {"status": "setup_complete"}


@router.post("/admin")
async def setup_admin(request: Request):
    """Configure the admin account during setup."""
    data = await request.json()
    return {"status": "admin_configured", "email": data.get("email")}


@router.post("/license")
async def setup_license(request: Request):
    """Activate license during setup."""
    data = await request.json()
    key = data.get("key", "")
    if key.startswith("HS-"):
        return {"status": "license_activated", "key": key}
    return JSONResponse(status_code=400, content={"detail": "Invalid license key"})


@router.post("/webserver")
async def setup_webserver(request: Request):
    """Configure web server during setup."""
    data = await request.json()
    return {"status": "webserver_configured", "engine": data.get("engine", "openlitespeed")}
