"""
HS-Panel Backend
service_manager/base.py — Base service manager with systemctl integration
"""
from __future__ import annotations

import subprocess
import logging
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceResult:
    """Uniform return type for all service manager operations."""
    def __init__(self, success: bool, message: str, data: Optional[dict] = None):
        self.success = success
        self.message = message
        self.data = data or {}

    def to_dict(self) -> dict:
        return {"success": self.success, "message": self.message, "data": self.data}


class BaseServiceManager:
    """
    Base class for all HS-Panel service managers.
    Provides systemctl integration and safe shell execution.
    """

    WRAP_SYSOP = "/usr/local/hspanel/bin/wrap_sysop"

    def _run(self, cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
        """Execute a command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error("Command timed out: %s", cmd)
            return 1, "", "Command timed out"
        except Exception as exc:  # noqa: BLE001
            logger.error("Command failed: %s — %s", cmd, exc)
            return 1, "", str(exc)

    def _sysop(self, *args: str) -> tuple[int, str, str]:
        """Invoke the setuid wrap_sysop helper (for privileged operations)."""
        return self._run([self.WRAP_SYSOP, *args])

    # ------------------------------------------------------------------
    # systemctl helpers
    # ------------------------------------------------------------------
    def systemctl(self, action: str, unit: str) -> ServiceResult:
        allowed_actions = {"start", "stop", "restart", "reload", "enable",
                           "disable", "status", "is-active", "is-enabled"}
        if action not in allowed_actions:
            return ServiceResult(False, f"Forbidden systemctl action: {action}")

        # Validate unit name (letters, digits, hyphen, dot, @, colon, slash)
        import re
        if not re.match(r'^[a-zA-Z0-9._@:\-/]+$', unit):
            return ServiceResult(False, f"Invalid unit name: {unit}")

        rc, out, err = self._run(["systemctl", action, unit])
        success = rc == 0
        return ServiceResult(success, out or err or f"systemctl {action} {unit}")

    def start_service(self, unit: str) -> ServiceResult:
        return self.systemctl("start", unit)

    def stop_service(self, unit: str) -> ServiceResult:
        return self.systemctl("stop", unit)

    def restart_service(self, unit: str) -> ServiceResult:
        return self.systemctl("restart", unit)

    def reload_service(self, unit: str) -> ServiceResult:
        return self.systemctl("reload", unit)

    def enable_service(self, unit: str) -> ServiceResult:
        return self.systemctl("enable", unit)

    def is_active(self, unit: str) -> bool:
        rc, _, _ = self._run(["systemctl", "is-active", "--quiet", unit])
        return rc == 0

    def service_status(self, unit: str) -> dict:
        rc, out, _ = self._run(["systemctl", "status", "--no-pager", unit])
        return {
            "unit": unit,
            "active": self.is_active(unit),
            "status_output": out,
        }

    def is_binary_available(self, name: str) -> bool:
        return shutil.which(name) is not None
