"""Developer Panel — Software Manager API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import subprocess
import shutil

router = APIRouter(prefix="/api/software", tags=["Software Manager"])


class SoftwareItem(BaseModel):
    id: str
    name: str
    category: str
    status: str
    version: str
    service_unit: str


def _detect_version(cmd: list) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip().split("\n")[0] if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _service_active(unit: str) -> str:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return "unknown"


CATALOG = [
    {
        "id": "openlitespeed",
        "name": "OpenLiteSpeed Web Server",
        "category": "web_server",
        "binary": "lshttpd",
        "service_unit": "lsws",
        "version_cmd": ["/usr/local/lsws/bin/lshttpd", "-v"],
    },
    {
        "id": "mariadb",
        "name": "MariaDB Database",
        "category": "database",
        "binary": "mysqld",
        "service_unit": "mariadb",
        "version_cmd": ["mariadb", "--version"],
    },
    {
        "id": "phpmyadmin",
        "name": "phpMyAdmin",
        "category": "database",
        "binary": None,
        "service_unit": "lsws",
        "version_cmd": None,
    },
    {
        "id": "powerdns",
        "name": "PowerDNS",
        "category": "dns",
        "binary": "pdns_server",
        "service_unit": "pdns",
        "version_cmd": ["pdns_server", "--version"],
    },
    {
        "id": "postfix",
        "name": "Postfix MTA",
        "category": "email",
        "binary": "postfix",
        "service_unit": "postfix",
        "version_cmd": ["postconf", "-d", "mail_version"],
    },
    {
        "id": "dovecot",
        "name": "Dovecot IMAP/POP3",
        "category": "email",
        "binary": "dovecot",
        "service_unit": "dovecot",
        "version_cmd": ["dovecot", "--version"],
    },
    {
        "id": "rainloop",
        "name": "Rainloop Webmail",
        "category": "email",
        "binary": None,
        "service_unit": "lsws",
        "version_cmd": None,
    },
    {
        "id": "pure-ftpd",
        "name": "Pure-FTPd",
        "category": "ftp",
        "binary": "pure-ftpd",
        "service_unit": "pure-ftpd",
        "version_cmd": ["pure-ftpd", "--help"],
    },
    {
        "id": "csf",
        "name": "ConfigServer Firewall (CSF)",
        "category": "security",
        "binary": "csf",
        "service_unit": "csf",
        "version_cmd": ["csf", "--version"],
    },
    {
        "id": "modsecurity",
        "name": "ModSecurity WAF",
        "category": "security",
        "binary": None,
        "service_unit": "lsws",
        "version_cmd": None,
    },
    {
        "id": "imunifyav",
        "name": "ImunifyAV",
        "category": "security",
        "binary": "imunify-antivirus",
        "service_unit": "imunify-antivirus",
        "version_cmd": ["imunify-antivirus", "version"],
    },
    {
        "id": "certbot",
        "name": "Certbot (Let's Encrypt)",
        "category": "ssl",
        "binary": "certbot",
        "service_unit": None,
        "version_cmd": ["certbot", "--version"],
    },
    {
        "id": "docker",
        "name": "Docker Engine",
        "category": "devops",
        "binary": "docker",
        "service_unit": "docker",
        "version_cmd": ["docker", "--version"],
    },
    {
        "id": "git",
        "name": "Git",
        "category": "devops",
        "binary": "git",
        "service_unit": None,
        "version_cmd": ["git", "--version"],
    },
]


@router.get("/list", response_model=List[SoftwareItem])
async def list_software():
    """List all managed hosting stack software with live status."""
    result = []
    for item in CATALOG:
        binary = item.get("binary")
        installed = shutil.which(binary) is not None if binary else False

        unit = item.get("service_unit")
        status = _service_active(unit) if unit and installed else ("installed" if installed else "not_installed")

        version = "n/a"
        if installed and item.get("version_cmd"):
            version = _detect_version(item["version_cmd"])

        result.append(SoftwareItem(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            status=status,
            version=version,
            service_unit=unit or "-",
        ))
    return result


@router.post("/install/{software_id}")
async def install_software(software_id: str):
    """Queue software installation for this panel server."""
    valid_ids = {item["id"] for item in CATALOG}
    if software_id not in valid_ids:
        raise HTTPException(status_code=404, detail=f"Unknown software: {software_id}")
    return {
        "success": True,
        "message": f"Installation of {software_id} queued. Run: sudo ./install.sh --mode install",
    }


@router.post("/restart/{service_unit}")
async def restart_service(service_unit: str):
    """Restart a systemd service by unit name."""
    valid_units = {item["service_unit"] for item in CATALOG if item.get("service_unit")}
    if service_unit not in valid_units:
        raise HTTPException(status_code=400, detail=f"Unit '{service_unit}' not in managed list")
    r = subprocess.run(["systemctl", "restart", service_unit], capture_output=True, text=True, timeout=30)
    return {"success": r.returncode == 0, "output": r.stdout + r.stderr}
