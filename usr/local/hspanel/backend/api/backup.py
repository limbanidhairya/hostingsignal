"""Backup endpoints backed by queue drop-in files."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token

router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(require_api_token)])

QUEUE_DIR = Path("/var/hspanel/queue")


class BackupRequest(BaseModel):
    username: str
    backup_type: str = "full"


@router.post("/enqueue")
def enqueue_backup(req: BackupRequest) -> dict:
    if req.backup_type not in {"full", "files", "database"}:
        raise HTTPException(status_code=400, detail="Invalid backup_type")

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid.uuid4())
    payload = {
        "id": job_id,
        "type": "generate_backup",
        "username": req.username,
        "backup_type": req.backup_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    job_file = QUEUE_DIR / f"{job_id}.json"
    job_file.write_text(json.dumps(payload, indent=2))

    return {"success": True, "message": "Backup job queued", "data": payload}
