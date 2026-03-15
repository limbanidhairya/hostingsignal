"""Internal service orchestration API."""
from __future__ import annotations

from pathlib import Path
import sys

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_current_admin
from .database import DevAdmin


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

router = APIRouter(prefix="/internal/services", tags=["Internal Services"])


class _UnavailableServiceOrchestrator:
    def __init__(self, reason: str):
        self.reason = reason

    def service_status(self, target: str | None = None) -> dict:
        return {"success": False, "detail": self.reason, "services": []}

    def service_action(self, action: str, target: str) -> dict:
        return {"success": False, "detail": self.reason, "action": action, "target": target}


try:
    from core.orchestrator.orchestrator import ServiceOrchestrator  # type: ignore  # noqa: E402

    orchestrator = ServiceOrchestrator()
except Exception as exc:
    orchestrator = _UnavailableServiceOrchestrator(f"Internal service orchestrator unavailable: {exc}")


class ServiceActionRequest(BaseModel):
    target: str = Field(..., description="Service name, group, or alias")


@router.get("/status")
async def service_status(
    target: str | None = None,
    _: DevAdmin = Depends(get_current_admin),
):
    result = orchestrator.service_status(target)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("detail", "Failed to fetch service status"))
    return result


@router.post("/start")
async def service_start(
    body: ServiceActionRequest,
    _: DevAdmin = Depends(get_current_admin),
):
    result = orchestrator.service_action("start", body.target)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/stop")
async def service_stop(
    body: ServiceActionRequest,
    _: DevAdmin = Depends(get_current_admin),
):
    result = orchestrator.service_action("stop", body.target)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/restart")
async def service_restart(
    body: ServiceActionRequest,
    _: DevAdmin = Depends(get_current_admin),
):
    result = orchestrator.service_action("restart", body.target)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result
