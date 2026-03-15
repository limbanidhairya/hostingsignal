"""Developer Panel - Container runtime API."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_current_admin
from .database import DevAdmin

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

router = APIRouter(prefix="/api/containers", tags=["Container Runner"])


class _UnavailableContainerRunner:
    def __init__(self, reason: str):
        self.reason = reason

    def available(self) -> dict:
        return {"available": False, "detail": self.reason}

    def _err(self) -> dict:
        return {"success": False, "detail": self.reason}

    def list_containers(self, include_all: bool = True) -> dict:
        return self._err()

    def run(
        self,
        image: str,
        name: str | None = None,
        detach: bool = True,
        ports: list[str] | None = None,
        env_vars: list[str] | None = None,
        command: str | None = None,
    ) -> dict:
        return self._err()

    def start(self, name: str) -> dict:
        return self._err()

    def stop(self, name: str, timeout_seconds: int = 10) -> dict:
        return self._err()

    def remove(self, name: str, force: bool = False) -> dict:
        return self._err()

    def logs(self, name: str, tail: int = 100) -> dict:
        return self._err()


runner = None
runner_error: str | None = None
_candidate_modules = [
    ROOT_DIR / "core" / "container-runner" / "container_runner.py",
    Path(__file__).resolve().parents[1] / "core" / "container-runner" / "container_runner.py",
]

for runner_module_path in _candidate_modules:
    if not runner_module_path.exists():
        continue
    try:
        _spec = importlib.util.spec_from_file_location("hs_container_runner", runner_module_path)
        if _spec is None or _spec.loader is None:
            raise RuntimeError(f"Unable to load container runner module from {runner_module_path}")
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_spec.name] = _module
        _spec.loader.exec_module(_module)
        runner = _module.ContainerRunner()
        runner_error = None
        break
    except Exception as exc:
        runner_error = str(exc)

if runner is None:
    if runner_error is None:
        runner_error = "Container runner module is not available in this runtime."
    runner = _UnavailableContainerRunner(runner_error)


class ContainerRunRequest(BaseModel):
    image: str = Field(..., description="Container image, e.g. nginx:alpine")
    name: str | None = None
    detach: bool = True
    ports: list[str] = Field(default_factory=list, description="Port mappings host:container")
    env_vars: list[str] = Field(default_factory=list, description="Environment KEY=VALUE entries")
    run_command: str | None = Field(default=None, description="Optional runtime command")


class ContainerActionRequest(BaseModel):
    name: str
    timeout_seconds: int = 10
    force: bool = False
    tail: int = 100


def _handle_failure(payload: dict, status_code: int = 400) -> dict:
    if payload.get("success"):
        return payload
    raise HTTPException(status_code=status_code, detail=payload.get("detail", "Container operation failed"))


@router.get("/status")
async def runtime_status(_: DevAdmin = Depends(get_current_admin)):
    return {"success": True, "data": runner.available()}


@router.get("/list")
async def list_containers(include_all: bool = True, _: DevAdmin = Depends(get_current_admin)):
    payload = runner.list_containers(include_all=include_all)
    return _handle_failure(payload)


@router.post("/run")
async def run_container(body: ContainerRunRequest, _: DevAdmin = Depends(get_current_admin)):
    payload = runner.run(
        image=body.image,
        name=body.name,
        detach=body.detach,
        ports=body.ports,
        env_vars=body.env_vars,
        command=body.run_command,
    )
    return _handle_failure(payload)


@router.post("/start")
async def start_container(body: ContainerActionRequest, _: DevAdmin = Depends(get_current_admin)):
    payload = runner.start(body.name)
    return _handle_failure(payload)


@router.post("/stop")
async def stop_container(body: ContainerActionRequest, _: DevAdmin = Depends(get_current_admin)):
    payload = runner.stop(body.name, timeout_seconds=body.timeout_seconds)
    return _handle_failure(payload)


@router.post("/remove")
async def remove_container(body: ContainerActionRequest, _: DevAdmin = Depends(get_current_admin)):
    payload = runner.remove(body.name, force=body.force)
    return _handle_failure(payload)


@router.post("/logs")
async def container_logs(body: ContainerActionRequest, _: DevAdmin = Depends(get_current_admin)):
    payload = runner.logs(body.name, tail=body.tail)
    return _handle_failure(payload)
