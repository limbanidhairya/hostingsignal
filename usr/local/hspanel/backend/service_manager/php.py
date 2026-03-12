"""
service_manager/php.py — PHP version manager for OpenLiteSpeed stack
Discovers installed lsphp versions and updates vhost PHP handler mappings.
"""
from __future__ import annotations

import re
import logging
from pathlib import Path

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

LSWS_FCGI_DIR = "/usr/local/lsws/fcgi-bin"
LSWS_VHOSTS_DIR = "/usr/local/lsws/conf/vhosts"


class PHPManager(BaseServiceManager):
    """Manage lsphp versions and vhost PHP bindings."""

    def list_installed_versions(self) -> list[str]:
        base = Path(LSWS_FCGI_DIR)
        if not base.exists():
            return []

        versions: list[str] = []
        for entry in base.iterdir():
            name = entry.name
            if not name.startswith("lsphp"):
                continue
            suffix = name.replace("lsphp", "")
            if suffix.isdigit():
                versions.append(suffix)
        return sorted(set(versions))

    def list_available_versions(self) -> list[str]:
        # Conservative known set; can be extended by distro metadata lookup later.
        return ["74", "80", "81", "82", "83", "84"]

    def install_version(self, version: str) -> ServiceResult:
        if not self._validate_version(version):
            return ServiceResult(False, f"Invalid PHP version: {version}")

        package = f"lsphp{version}"
        if self.is_binary_available("apt-get"):
            cmd = ["apt-get", "install", "-y", package, f"{package}-common", f"{package}-mysql"]
        elif self.is_binary_available("dnf"):
            cmd = ["dnf", "install", "-y", package]
        else:
            return ServiceResult(False, "Unsupported package manager")

        rc, out, err = self._run(cmd, timeout=120)
        if rc != 0:
            return ServiceResult(False, f"Failed to install {package}: {err or out}")
        return ServiceResult(True, f"Installed PHP version: {version}")

    def uninstall_version(self, version: str) -> ServiceResult:
        if not self._validate_version(version):
            return ServiceResult(False, f"Invalid PHP version: {version}")

        package = f"lsphp{version}"
        if self.is_binary_available("apt-get"):
            cmd = ["apt-get", "remove", "-y", package]
        elif self.is_binary_available("dnf"):
            cmd = ["dnf", "remove", "-y", package]
        else:
            return ServiceResult(False, "Unsupported package manager")

        rc, out, err = self._run(cmd, timeout=120)
        if rc != 0:
            return ServiceResult(False, f"Failed to remove {package}: {err or out}")
        return ServiceResult(True, f"Removed PHP version: {version}")

    def set_vhost_php_version(self, domain: str, version: str) -> ServiceResult:
        if not domain or "." not in domain:
            return ServiceResult(False, f"Invalid domain: {domain}")
        if not self._validate_version(version):
            return ServiceResult(False, f"Invalid PHP version: {version}")

        conf_file = Path(LSWS_VHOSTS_DIR) / domain / "vhconf.conf"
        if not conf_file.exists():
            return ServiceResult(False, f"Vhost config not found: {conf_file}")

        desired = f"lsphp{version}"
        lines = conf_file.read_text().splitlines()
        updated: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("handler") and "lsphp" in stripped:
                # Replace any lsphpXX handler token on the line.
                updated.append(re.sub(r"lsphp\d+", desired, line))
            else:
                updated.append(line)

        conf_file.write_text("\n".join(updated) + "\n")
        reload_result = self.restart_service("lsws")
        if not reload_result.success:
            return reload_result

        return ServiceResult(True, f"Set {domain} PHP version to {version}")

    @staticmethod
    def _validate_version(version: str) -> bool:
        return bool(re.match(r"^\d{2}$", version))
