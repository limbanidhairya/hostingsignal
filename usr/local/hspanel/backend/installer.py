"""Backend installer/bootstrap module for HS-Panel API runtime."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .service_manager.base import ServiceResult

BACKEND_ROOT = Path("/usr/local/hspanel/backend")
VENV_DIR = BACKEND_ROOT / "venv"
REQUIREMENTS_FILE = BACKEND_ROOT / "requirements.txt"
ENV_FILE = BACKEND_ROOT / ".env"
RUNTIME_DIRS = [
    Path("/var/hspanel/logs"),
    Path("/var/hspanel/queue"),
    Path("/var/hspanel/backups"),
    Path("/var/hspanel/users"),
    Path("/var/hspanel/userdata"),
]


class BackendInstaller:
    """Install and configure HS-Panel backend runtime prerequisites."""

    def run_all(self) -> ServiceResult:
        for step in (self.ensure_runtime_dirs, self.ensure_env_file, self.install_python_dependencies):
            result = step()
            if not result.success:
                return result
        return ServiceResult(True, "Backend bootstrap completed")

    def ensure_runtime_dirs(self) -> ServiceResult:
        try:
            for directory in RUNTIME_DIRS:
                directory.mkdir(parents=True, exist_ok=True)
            return ServiceResult(True, "Runtime directories are ready")
        except Exception as exc:  # noqa: BLE001
            return ServiceResult(False, f"Failed to create runtime directories: {exc}")

    def ensure_env_file(self) -> ServiceResult:
        try:
            if ENV_FILE.exists():
                return ServiceResult(True, ".env already exists")

            panel_secret = self._load_secret("PANEL_SECRET_KEY", default="change-me")
            db_password = self._load_secret("PANEL_DB_PASSWORD", default="change-me")

            content = (
                "ENV=production\n"
                "HOST=0.0.0.0\n"
                "PORT=2083\n"
                "DATABASE_URL=sqlite+aiosqlite:////var/hspanel/hspanel.db\n"
                f"PANEL_SECRET_KEY={panel_secret}\n"
                f"PANEL_DB_PASSWORD={db_password}\n"
            )
            ENV_FILE.write_text(content)
            os.chmod(ENV_FILE, 0o600)
            return ServiceResult(True, "Created backend .env file")
        except Exception as exc:  # noqa: BLE001
            return ServiceResult(False, f"Failed to write .env: {exc}")

    def install_python_dependencies(self) -> ServiceResult:
        if not REQUIREMENTS_FILE.exists():
            return ServiceResult(False, f"Requirements not found: {REQUIREMENTS_FILE}")

        try:
            if not VENV_DIR.exists():
                rc, out, err = self._run(["python3", "-m", "venv", str(VENV_DIR)], timeout=120)
                if rc != 0:
                    return ServiceResult(False, f"Failed to create virtualenv: {err or out}")

            pip_bin = VENV_DIR / "bin" / "pip"
            rc, out, err = self._run([str(pip_bin), "install", "--upgrade", "pip", "setuptools", "wheel"], timeout=240)
            if rc != 0:
                return ServiceResult(False, f"Failed to update pip tooling: {err or out}")

            rc, out, err = self._run([str(pip_bin), "install", "-r", str(REQUIREMENTS_FILE)], timeout=600)
            if rc != 0:
                return ServiceResult(False, f"Failed to install requirements: {err or out}")

            return ServiceResult(True, "Python dependencies installed")
        except Exception as exc:  # noqa: BLE001
            return ServiceResult(False, f"Dependency installation failed: {exc}")

    def _load_secret(self, key: str, default: str = "") -> str:
        sec_file = Path("/usr/local/hspanel/config/.secrets")
        if not sec_file.exists():
            return default

        for line in sec_file.read_text().splitlines():
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
        return default

    @staticmethod
    def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
