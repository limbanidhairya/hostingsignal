"""Cron management endpoints for per-user cron files."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token

router = APIRouter(prefix="/api/cron", tags=["cron"], dependencies=[Depends(require_api_token)])

CRON_BASE = Path("/var/hspanel/users")


class CronEntryRequest(BaseModel):
    username: str
    expression: str
    command: str


@router.post("/add")
def add_cron(req: CronEntryRequest) -> dict:
    if not req.username.strip() or not req.expression.strip() or not req.command.strip():
        raise HTTPException(status_code=400, detail="username, expression and command are required")

    cron_file = CRON_BASE / req.username / "cron.tab"
    cron_file.parent.mkdir(parents=True, exist_ok=True)

    entry = f"{req.expression} {req.command}".strip()
    lines = cron_file.read_text().splitlines() if cron_file.exists() else []
    if entry not in lines:
        lines.append(entry)
        cron_file.write_text("\n".join(lines) + "\n")

    return {"success": True, "message": "Cron entry added", "data": {"entry": entry}}


@router.get("/list/{username}")
def list_cron(username: str) -> dict:
    cron_file = CRON_BASE / username / "cron.tab"
    entries = cron_file.read_text().splitlines() if cron_file.exists() else []
    return {"success": True, "data": entries}


@router.delete("/clear/{username}")
def clear_cron(username: str) -> dict:
    cron_file = CRON_BASE / username / "cron.tab"
    if cron_file.exists():
        cron_file.unlink()
    return {"success": True, "message": "Cron entries cleared"}
