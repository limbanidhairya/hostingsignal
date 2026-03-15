"""
service_manager/ftp.py — Pure-FTPd manager
Handles FTP virtual users for hosting accounts.
"""
from __future__ import annotations

import re
import pwd
import subprocess
import logging
from pathlib import Path

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

PURE_PW_BIN = "/usr/bin/pure-pw"
PUREDB_FILE = "/etc/pure-ftpd/pureftpd.pdb"
DEFAULT_USERS_BASE = "/var/hspanel/users"


class FTPManager(BaseServiceManager):
    """Manage Pure-FTPd users and service lifecycle."""

    def reload(self) -> ServiceResult:
        return self.restart_service("pure-ftpd")

    def status(self) -> dict:
        return self.service_status("pure-ftpd")

    def create_ftp_user(
        self,
        username: str,
        password: str,
        home: str,
        system_user: str = "hspanel",
    ) -> ServiceResult:
        if not self._validate_username(username):
            return ServiceResult(False, f"Invalid FTP username: {username}")

        if not password or len(password) < 8:
            return ServiceResult(False, "FTP password must be at least 8 characters")

        home_path = Path(home)
        home_path.mkdir(parents=True, exist_ok=True)

        try:
            pwent = pwd.getpwnam(system_user)
        except KeyError:
            return ServiceResult(False, f"System user not found: {system_user}")

        cmd = [
            PURE_PW_BIN,
            "useradd",
            username,
            "-u",
            str(pwent.pw_uid),
            "-g",
            str(pwent.pw_gid),
            "-d",
            str(home_path),
            "-m",
        ]

        rc, out, err = self._run_with_password(cmd, password)
        if rc != 0:
            return ServiceResult(False, f"Failed to create FTP user: {err or out}")

        mkdb = self._rebuild_db()
        if not mkdb.success:
            return mkdb

        return ServiceResult(True, f"FTP user created: {username}", {"home": str(home_path)})

    def delete_ftp_user(self, username: str) -> ServiceResult:
        if not self._validate_username(username):
            return ServiceResult(False, f"Invalid FTP username: {username}")

        rc, out, err = self._run([PURE_PW_BIN, "userdel", username, "-m"], timeout=20)
        if rc != 0:
            return ServiceResult(False, f"Failed to delete FTP user: {err or out}")

        mkdb = self._rebuild_db()
        if not mkdb.success:
            return mkdb

        return ServiceResult(True, f"FTP user deleted: {username}")

    def list_ftp_users(self) -> list[str]:
        rc, out, _ = self._run([PURE_PW_BIN, "list"], timeout=20)
        if rc != 0 or not out:
            return []

        users: list[str] = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            users.append(line.split(maxsplit=1)[0])
        return users

    def change_ftp_password(self, username: str, new_password: str) -> ServiceResult:
        if not self._validate_username(username):
            return ServiceResult(False, f"Invalid FTP username: {username}")

        if not new_password or len(new_password) < 8:
            return ServiceResult(False, "FTP password must be at least 8 characters")

        rc, out, err = self._run_with_password([PURE_PW_BIN, "passwd", username, "-m"], new_password)
        if rc != 0:
            return ServiceResult(False, f"Failed to change FTP password: {err or out}")

        mkdb = self._rebuild_db()
        if not mkdb.success:
            return mkdb

        return ServiceResult(True, f"FTP password updated: {username}")

    def _rebuild_db(self) -> ServiceResult:
        rc, out, err = self._run([PURE_PW_BIN, "mkdb", PUREDB_FILE], timeout=20)
        if rc != 0:
            return ServiceResult(False, f"Failed to rebuild puredb: {err or out}")
        # Best-effort service reload: in containerised / dev environments
        # systemctl may not be available. The DB rebuild itself is sufficient
        # for the user changes to take effect when the service is already running.
        restart = self.restart_service("pure-ftpd")
        if not restart.success:
            logger.warning(
                "pure-ftpd service reload failed (may be expected in containers): %s",
                restart.message,
            )
        return ServiceResult(True, "Pure-FTPd database rebuilt")

    @staticmethod
    def _validate_username(username: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9._-]{1,64}$", username))

    @staticmethod
    def _default_home(username: str) -> str:
        return str(Path(DEFAULT_USERS_BASE) / username / "public_html")

    def _run_with_password(self, cmd: list[str], password: str) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                cmd,
                input=f"{password}\n{password}\n",
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as exc:  # noqa: BLE001
            logger.error("Command failed: %s — %s", cmd, exc)
            return 1, "", str(exc)
