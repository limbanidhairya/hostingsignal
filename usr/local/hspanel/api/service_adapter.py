#!/usr/bin/env python3
"""
HostingSignal — Service Adapter Layer
Unified interface to manage all hosting stack services from Python.
Called by the panel daemon and API routes.
"""
import subprocess
import shutil
import os
from typing import Dict, Optional

PANEL_ROOT = "/usr/local/hspanel"
PANEL_VAR = "/var/hspanel"

SERVICES: Dict[str, Dict] = {
    "lsws": {
        "label": "OpenLiteSpeed Web Server",
        "systemd": "lsws",
        "reload_cmd": ["/usr/local/lsws/bin/lswsctrl", "restart"],
        "config_test": None,
        "log": "/usr/local/lsws/logs/error.log",
    },
    "mariadb": {
        "label": "MariaDB Database",
        "systemd": "mariadb",
        "reload_cmd": ["systemctl", "reload", "mariadb"],
        "config_test": None,
        "log": "/var/log/mysql/error.log",
    },
    "mysql": {
        "label": "MySQL Database",
        "systemd": "mysql",
        "reload_cmd": ["systemctl", "reload", "mysql"],
        "config_test": None,
        "log": "/var/log/mysql/error.log",
    },
    "postfix": {
        "label": "Postfix MTA",
        "systemd": "postfix",
        "reload_cmd": ["postfix", "reload"],
        "config_test": ["postfix", "check"],
        "log": "/var/log/mail.log",
    },
    "dovecot": {
        "label": "Dovecot IMAP/POP3",
        "systemd": "dovecot",
        "reload_cmd": ["doveadm", "reload"],
        "config_test": ["doveconf", "-n"],
        "log": "/var/log/dovecot.log",
    },
    "pdns": {
        "label": "PowerDNS Server",
        "systemd": "pdns",
        "reload_cmd": ["pdns_control", "cycle"],
        "config_test": None,
        "log": "/var/log/pdns.log",
    },
    "pure-ftpd": {
        "label": "Pure-FTPd",
        "systemd": "pure-ftpd",
        "reload_cmd": ["systemctl", "reload", "pure-ftpd"],
        "config_test": None,
        "log": "/var/log/pure-ftpd/transfer.log",
    },
    "docker": {
        "label": "Docker Engine",
        "systemd": "docker",
        "reload_cmd": ["systemctl", "reload", "docker"],
        "config_test": None,
        "log": "/var/log/docker.log",
    },
    "csf": {
        "label": "ConfigServer Firewall",
        "systemd": "csf",
        "reload_cmd": ["csf", "-r"],
        "config_test": None,
        "log": "/var/log/lfd.log",
    },
}


def _run(cmd: list, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def service_status(name: str) -> Dict:
    svc = SERVICES.get(name)
    if not svc:
        return {"name": name, "status": "unknown", "error": "Service not in registry"}

    result = _run(["systemctl", "is-active", svc["systemd"]])
    active = result.stdout.strip()
    enabled_result = _run(["systemctl", "is-enabled", svc["systemd"]])
    enabled = enabled_result.stdout.strip()
    return {
        "name": name,
        "label": svc["label"],
        "status": active,
        "enabled": enabled,
        "systemd_unit": svc["systemd"],
    }


def all_service_statuses() -> list:
    return [service_status(name) for name in SERVICES]


def reload_service(name: str) -> Dict:
    svc = SERVICES.get(name)
    if not svc:
        return {"success": False, "error": f"Unknown service: {name}"}

    if svc.get("config_test"):
        test = _run(svc["config_test"])
        if test.returncode != 0:
            return {
                "success": False,
                "error": f"Config test failed for {name}",
                "output": test.stderr,
            }

    result = _run(svc["reload_cmd"])
    return {
        "success": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }


def restart_service(name: str) -> Dict:
    svc = SERVICES.get(name)
    if not svc:
        return {"success": False, "error": f"Unknown service: {name}"}
    result = _run(["systemctl", "restart", svc["systemd"]])
    return {
        "success": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }


def start_service(name: str) -> Dict:
    svc = SERVICES.get(name)
    if not svc:
        return {"success": False, "error": f"Unknown service: {name}"}
    result = _run(["systemctl", "start", svc["systemd"]])
    return {
        "success": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }


def stop_service(name: str) -> Dict:
    svc = SERVICES.get(name)
    if not svc:
        return {"success": False, "error": f"Unknown service: {name}"}
    result = _run(["systemctl", "stop", svc["systemd"]])
    return {
        "success": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }


def get_installed_php_versions() -> list:
    versions = []
    lsws_base = "/usr/local/lsws"
    if not os.path.isdir(lsws_base):
        return versions
    for entry in os.scandir(lsws_base):
        if entry.is_dir() and entry.name.startswith("lsphp"):
            php_bin = os.path.join(entry.path, "bin", "php")
            if os.access(php_bin, os.X_OK):
                result = _run([php_bin, "-r", "echo PHP_VERSION;"])
                versions.append({
                    "handler": entry.name,
                    "binary": php_bin,
                    "version": result.stdout.strip() if result.returncode == 0 else "?",
                })
    return sorted(versions, key=lambda x: x["handler"])


def csf_allow_ip(ip: str) -> Dict:
    if not shutil.which("csf"):
        return {"success": False, "error": "CSF not installed"}
    result = _run(["csf", "-a", ip])
    return {"success": result.returncode == 0, "output": result.stdout + result.stderr}


def csf_deny_ip(ip: str) -> Dict:
    if not shutil.which("csf"):
        return {"success": False, "error": "CSF not installed"}
    result = _run(["csf", "-d", ip])
    return {"success": result.returncode == 0, "output": result.stdout + result.stderr}


def certbot_issue(domain: str, email: str, webroot: Optional[str] = None) -> Dict:
    if not shutil.which("certbot"):
        return {"success": False, "error": "certbot not installed"}
    cmd = [
        "certbot", "certonly",
        "--non-interactive",
        "--agree-tos",
        "--email", email,
        "-d", domain,
    ]
    if webroot:
        cmd += ["--webroot", "-w", webroot]
    else:
        cmd += ["--standalone"]
    result = _run(cmd)
    return {
        "success": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }


def certbot_renew() -> Dict:
    if not shutil.which("certbot"):
        return {"success": False, "error": "certbot not installed"}
    result = _run(["certbot", "renew", "--quiet"])
    return {"success": result.returncode == 0, "output": result.stdout + result.stderr}
