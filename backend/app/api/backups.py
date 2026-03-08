"""
HostingSignal Panel — Backup Management API
Manual, scheduled, and remote backups.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.core.security import get_current_user
from app.services.backup_manager import BackupManager

router = APIRouter(prefix="/api/backups", tags=["Backups"])

backup_mgr = BackupManager()


class CreateBackupRequest(BaseModel):
    backup_type: str = "full"  # full | incremental | files_only | database_only
    websites: Optional[List[str]] = None  # None = all websites
    databases: Optional[List[str]] = None
    include_emails: bool = True
    compression: str = "gzip"  # gzip | zstd | none
    destination: str = "local"  # local | s3 | sftp


class ScheduleBackupRequest(BaseModel):
    name: str
    backup_type: str = "full"
    schedule: str = "0 2 * * *"  # cron format — default daily at 2am
    retention_days: int = 30
    destination: str = "local"
    websites: Optional[List[str]] = None
    enabled: bool = True


class RemoteBackupConfig(BaseModel):
    provider: str  # s3 | sftp | gcs
    bucket: Optional[str] = None
    endpoint: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    sftp_host: Optional[str] = None
    sftp_user: Optional[str] = None
    sftp_password: Optional[str] = None
    sftp_path: Optional[str] = None


@router.get("/")
async def list_backups(current_user: dict = Depends(get_current_user)):
    """List all available backups."""
    try:
        backups = backup_mgr.list_backups()
        return {"backups": backups, "total": len(backups)}
    except Exception as e:
        return {"backups": [], "error": str(e)}


@router.post("/create")
async def create_backup(
    body: CreateBackupRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new backup."""
    try:
        result = backup_mgr.create_backup(
            backup_type=body.backup_type,
            websites=body.websites,
            compression=body.compression,
        )
        return {
            "status": "success",
            "backup_type": body.backup_type,
            "destination": body.destination,
            "message": "Backup job started.",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Restore from a backup."""
    try:
        result = backup_mgr.restore_backup(backup_id)
        return {
            "status": "success",
            "backup_id": backup_id,
            "message": "Restore job started.",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a backup."""
    try:
        result = backup_mgr.delete_backup(backup_id)
        return {"status": "success", "message": f"Backup {backup_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{backup_id}")
async def download_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get download link for a backup."""
    try:
        path = backup_mgr.get_backup_path(backup_id)
        if not path:
            raise HTTPException(status_code=404, detail="Backup not found")
        return {"status": "success", "download_path": path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Scheduled Backups ────────────────────────────────────────────────────────

@router.get("/schedules")
async def list_backup_schedules(current_user: dict = Depends(get_current_user)):
    """List all backup schedules."""
    try:
        schedules = backup_mgr.list_schedules()
        return {"schedules": schedules, "total": len(schedules)}
    except Exception as e:
        return {"schedules": [], "error": str(e)}


@router.post("/schedules")
async def create_backup_schedule(
    body: ScheduleBackupRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a scheduled backup."""
    try:
        result = backup_mgr.create_schedule(
            name=body.name,
            backup_type=body.backup_type,
            schedule=body.schedule,
            retention_days=body.retention_days,
        )
        return {
            "status": "success",
            "name": body.name,
            "schedule": body.schedule,
            "message": "Backup schedule created.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_backup_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a backup schedule."""
    try:
        result = backup_mgr.delete_schedule(schedule_id)
        return {"status": "success", "message": f"Schedule {schedule_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Remote Backup Configuration ─────────────────────────────────────────────

@router.post("/remote-config")
async def configure_remote_backup(
    body: RemoteBackupConfig,
    current_user: dict = Depends(get_current_user),
):
    """Configure remote backup destination."""
    try:
        result = backup_mgr.configure_remote(
            provider=body.provider,
            config=body.model_dump(exclude_none=True),
        )
        return {
            "status": "success",
            "provider": body.provider,
            "message": "Remote backup configured.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
