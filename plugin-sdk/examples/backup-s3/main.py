"""
Backup S3 Plugin — Automated S3-compatible backup plugin for HostingSignal Panel
Syncs completed backups to Amazon S3, MinIO, DigitalOcean Spaces, or similar storage.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("plugin.backup_s3")
CONFIG_PATH = "/usr/local/hostingsignal/plugins/backup-s3/config.json"
DEFAULT_CONFIG = {
    "endpoint_url": "",
    "access_key": "",
    "secret_key": "",
    "bucket": "hostingsignal-backups",
    "region": "us-east-1",
    "prefix": "backups/",
    "retention_days": 30,
    "auto_upload": True,
}


def register_hooks(event_bus):
    event_bus.on("backup.completed", on_backup_completed, plugin_name="backup_s3")
    event_bus.on("cron.daily", on_daily_cleanup, plugin_name="backup_s3")
    logger.info("Backup S3 plugin registered")


def _load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG


def _get_s3_client(config):
    try:
        import boto3
        session = boto3.session.Session()
        kwargs = {
            "aws_access_key_id": config["access_key"],
            "aws_secret_access_key": config["secret_key"],
            "region_name": config["region"],
        }
        if config.get("endpoint_url"):
            kwargs["endpoint_url"] = config["endpoint_url"]
        return session.client("s3", **kwargs)
    except ImportError:
        logger.error("boto3 is not installed. Run: pip install boto3")
        return None


def on_backup_completed(data):
    config = _load_config()
    if not config.get("auto_upload"):
        return

    backup_path = data.get("file_path", "")
    domain = data.get("domain", "unknown")
    if not backup_path or not os.path.exists(backup_path):
        return

    s3 = _get_s3_client(config)
    if not s3:
        return

    filename = os.path.basename(backup_path)
    s3_key = f"{config['prefix']}{domain}/{filename}"

    try:
        s3.upload_file(backup_path, config["bucket"], s3_key)
        logger.info(f"Backup uploaded to S3: {s3_key}")
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")


def on_daily_cleanup(data):
    """Clean up old backups from S3 based on retention policy."""
    config = _load_config()
    if config["retention_days"] <= 0:
        return

    s3 = _get_s3_client(config)
    if not s3:
        return

    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=config["retention_days"])
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=config["bucket"], Prefix=config["prefix"]):
            for obj in page.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=None) < cutoff:
                    s3.delete_object(Bucket=config["bucket"], Key=obj["Key"])
                    logger.info(f"Deleted old backup: {obj['Key']}")
    except Exception as e:
        logger.error(f"S3 cleanup failed: {e}")


def configure(request_data):
    """API handler: save S3 configuration."""
    config = _load_config()
    for key in ["endpoint_url", "access_key", "secret_key", "bucket", "region", "prefix", "retention_days", "auto_upload"]:
        if key in request_data:
            config[key] = request_data[key]

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "ok", "config": {k: v for k, v in config.items() if k not in ("access_key", "secret_key")}}


def upload_backup(request_data):
    """API handler: manually upload a backup file."""
    backup_path = request_data.get("file_path", "")
    domain = request_data.get("domain", "manual")
    if not os.path.exists(backup_path):
        return {"error": f"File not found: {backup_path}"}

    on_backup_completed({"file_path": backup_path, "domain": domain})
    return {"status": "uploaded", "file": backup_path}


def list_backups(request_data):
    """API handler: list backups in S3."""
    config = _load_config()
    s3 = _get_s3_client(config)
    if not s3:
        return {"error": "S3 client not configured"}

    try:
        resp = s3.list_objects_v2(Bucket=config["bucket"], Prefix=config["prefix"], MaxKeys=100)
        items = [{
            "key": obj["Key"],
            "size": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        } for obj in resp.get("Contents", [])]
        return {"backups": items, "bucket": config["bucket"]}
    except Exception as e:
        return {"error": str(e)}


def cleanup():
    logger.info("Backup S3 plugin unloaded")
