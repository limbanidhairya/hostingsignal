"""Developer Panel - Server shell command execution API."""
from __future__ import annotations

import os
import subprocess
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_current_admin
from .database import DevAdmin

router = APIRouter(prefix="/api/shell", tags=["Shell"])


class ShellExecuteRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4000, description="Shell command to execute")
    cwd: str | None = Field(default=None, description="Optional working directory")
    timeout_seconds: int = Field(default=20, ge=1, le=120, description="Execution timeout in seconds")


def _validate_cwd(value: str | None) -> str | None:
    if value is None:
        return None
    if not os.path.isabs(value):
        raise HTTPException(status_code=400, detail="cwd must be an absolute path")
    if not os.path.isdir(value):
        raise HTTPException(status_code=400, detail=f"cwd does not exist: {value}")
    return value


@router.post("/execute")
async def execute_command(body: ShellExecuteRequest, _: DevAdmin = Depends(get_current_admin)):
    command = body.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="command is required")

    cwd = _validate_cwd(body.cwd.strip() if body.cwd else None)
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=body.timeout_seconds,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "success": False,
            "command": command,
            "cwd": cwd,
            "exit_code": None,
            "duration_ms": duration_ms,
            "stdout": (exc.stdout or "")[:200000],
            "stderr": f"Command timed out after {body.timeout_seconds} seconds.",
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))

    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "success": completed.returncode == 0,
        "command": command,
        "cwd": cwd,
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "stdout": (completed.stdout or "")[:200000],
        "stderr": (completed.stderr or "")[:200000],
    }
