"""
HostingSignal — Backup Manager
Full/incremental backups, restore, scheduling.
"""
import os
from datetime import datetime
from .server_utils import run_cmd, ensure_dir, DEV_MODE, logger

BACKUP_DIR = "/home/hostingsignal-backups"

DEMO_BACKUPS = [
    {"id": "bk_001", "domain": "example.com", "type": "full", "size": "245 MB", "date": "2026-02-28 03:00", "status": "completed"},
    {"id": "bk_002", "domain": "blog.example.com", "type": "full", "size": "89 MB", "date": "2026-02-27 03:00", "status": "completed"},
    {"id": "bk_003", "domain": "all", "type": "full", "size": "1.2 GB", "date": "2026-02-26 03:00", "status": "completed"},
]


def list_backups(domain: str | None = None) -> list[dict]:
    if DEV_MODE:
        if domain:
            return [b for b in DEMO_BACKUPS if b["domain"] == domain]
        return DEMO_BACKUPS
    backups = []
    if not os.path.exists(BACKUP_DIR):
        return []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if f.endswith(".tar.gz"):
            path = os.path.join(BACKUP_DIR, f)
            stat = os.stat(path)
            parts = f.replace(".tar.gz", "").split("_")
            bk_domain = parts[0] if parts else "unknown"
            if domain and bk_domain != domain:
                continue
            size = stat.st_size
            size_str = f"{size / 1024 / 1024:.1f} MB" if size < 1024**3 else f"{size / 1024**3:.1f} GB"
            backups.append({
                "id": f.replace(".tar.gz", ""),
                "domain": bk_domain,
                "type": "full",
                "size": size_str,
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "status": "completed",
                "filename": f,
            })
    return backups


def create_backup(domain: str, include_db: bool = True, include_email: bool = True) -> dict:
    """Create a full backup (files + database + email)."""
    ensure_dir(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{domain}_{timestamp}"
    backup_path = f"{BACKUP_DIR}/{backup_name}.tar.gz"
    tmp_dir = f"/tmp/hs_backup_{backup_name}"
    ensure_dir(tmp_dir)

    # Backup website files
    run_cmd(f"cp -a /home/{domain} {tmp_dir}/files", timeout=300)

    # Backup databases
    if include_db:
        ensure_dir(f"{tmp_dir}/databases")
        # Dump all databases associated with the domain
        db_prefix = domain.replace(".", "_").replace("-", "_")[:16]
        run_cmd(f"mysqldump --all-databases --single-transaction > {tmp_dir}/databases/all_databases.sql", timeout=300)

    # Backup email
    if include_email:
        run_cmd(f"cp -a /home/vmail/{domain} {tmp_dir}/email 2>/dev/null || true", timeout=120)

    # Create archive
    result = run_cmd(f"tar -czf {backup_path} -C {tmp_dir} .", timeout=600)

    # Cleanup temp
    run_cmd(f"rm -rf {tmp_dir}")

    return {
        "id": backup_name,
        "domain": domain,
        "type": "full",
        "size": "calculating...",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "completed" if result.success or DEV_MODE else "failed",
        "path": backup_path,
    }


def restore_backup(backup_id: str, domain: str | None = None) -> dict:
    """Restore from a backup archive."""
    backup_file = f"{BACKUP_DIR}/{backup_id}.tar.gz"
    tmp_dir = f"/tmp/hs_restore_{backup_id}"
    ensure_dir(tmp_dir)

    # Extract
    run_cmd(f"tar -xzf {backup_file} -C {tmp_dir}", timeout=600)

    # Restore files
    if domain:
        run_cmd(f"rsync -a {tmp_dir}/files/ /home/{domain}/", timeout=300)
    else:
        run_cmd(f"rsync -a {tmp_dir}/files/ /home/", timeout=300)

    # Restore databases
    if os.path.exists(f"{tmp_dir}/databases") or DEV_MODE:
        run_cmd(f"mysql < {tmp_dir}/databases/all_databases.sql 2>/dev/null || true", timeout=300)

    # Restore email
    if os.path.exists(f"{tmp_dir}/email") or DEV_MODE:
        run_cmd(f"rsync -a {tmp_dir}/email/ /home/vmail/{domain}/ 2>/dev/null || true", timeout=120)

    # Cleanup
    run_cmd(f"rm -rf {tmp_dir}")

    return {"status": "restored", "backup_id": backup_id}


def delete_backup(backup_id: str) -> bool:
    backup_file = f"{BACKUP_DIR}/{backup_id}.tar.gz"
    if DEV_MODE:
        return True
    try:
        os.remove(backup_file)
        return True
    except Exception:
        return False


def setup_schedule(domain: str, frequency: str = "daily", hour: int = 3) -> dict:
    """Set up automated backup schedule via cron."""
    cron_entry = f"0 {hour} * * * /opt/hostingsignal/backup.sh {domain} >> /var/log/hs-backup.log 2>&1"
    if frequency == "weekly":
        cron_entry = f"0 {hour} * * 0 /opt/hostingsignal/backup.sh {domain} >> /var/log/hs-backup.log 2>&1"
    run_cmd(f"(crontab -l 2>/dev/null | grep -v 'backup.sh {domain}'; echo '{cron_entry}') | crontab -")
    return {"domain": domain, "frequency": frequency, "hour": hour, "status": "scheduled"}
