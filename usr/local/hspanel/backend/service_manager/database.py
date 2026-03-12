"""
service_manager/database.py — MariaDB/MySQL database and user manager
Creates/deletes databases and DB users via subprocess to mysql CLI.
"""
from __future__ import annotations

import re
import logging
import secrets
import string

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

MYSQL_SOCKET = "/var/run/mysqld/mysqld.sock"


class DatabaseManager(BaseServiceManager):
    """Manage MariaDB/MySQL databases and users on behalf of panel users."""

    # ------------------------------------------------------------------
    # Service control
    # ------------------------------------------------------------------
    def restart(self) -> ServiceResult:
        return self.restart_service("mariadb")

    def reload(self) -> ServiceResult:
        return self.reload_service("mariadb")

    def status(self) -> dict:
        return self.service_status("mariadb")

    # ------------------------------------------------------------------
    # Database CRUD
    # ------------------------------------------------------------------
    def create_database(self, db_name: str, owner_user: str = "") -> ServiceResult:
        if not self._validate_db_identifier(db_name):
            return ServiceResult(False, f"Invalid database name: {db_name}")

        sql = f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        rc, out, err = self._mysql(sql)
        if rc != 0:
            return ServiceResult(False, f"Failed to create database: {err}")

        if owner_user:
            grant_result = self.grant_privileges(db_name, owner_user)
            if not grant_result.success:
                logger.warning("DB created but grant failed: %s", grant_result.message)

        return ServiceResult(True, f"Database created: {db_name}", {"database": db_name})

    def delete_database(self, db_name: str) -> ServiceResult:
        if not self._validate_db_identifier(db_name):
            return ServiceResult(False, f"Invalid database name: {db_name}")

        # Safety: never delete system databases
        if db_name.lower() in {"mysql", "information_schema", "performance_schema",
                                "sys", "hspanel"}:
            return ServiceResult(False, f"Cannot delete system database: {db_name}")

        sql = f"DROP DATABASE IF EXISTS `{db_name}`;"
        rc, _, err = self._mysql(sql)
        return ServiceResult(rc == 0, f"Database deleted: {db_name}" if rc == 0 else err)

    def list_databases(self, exclude_system: bool = True) -> list[str]:
        system_dbs = {"mysql", "information_schema", "performance_schema", "sys"}
        sql = "SHOW DATABASES;"
        rc, out, _ = self._mysql(sql)
        if rc != 0:
            return []
        dbs = [l.strip() for l in out.splitlines() if l.strip() and l.strip() != "Database"]
        if exclude_system:
            dbs = [d for d in dbs if d.lower() not in system_dbs]
        return dbs

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------
    def create_db_user(
        self, username: str, password: str | None = None
    ) -> ServiceResult:
        if not self._validate_db_identifier(username):
            return ServiceResult(False, f"Invalid username: {username}")

        if password is None:
            password = self._generate_password()

        sql = (
            f"CREATE USER IF NOT EXISTS '{username}'@'localhost' "
            f"IDENTIFIED BY '{self._escape_sql_string(password)}';"
        )
        rc, _, err = self._mysql(sql)
        if rc != 0:
            return ServiceResult(False, f"Failed to create user: {err}")
        return ServiceResult(
            True,
            f"DB user created: {username}",
            {"username": username, "password": password},
        )

    def delete_db_user(self, username: str) -> ServiceResult:
        if not self._validate_db_identifier(username):
            return ServiceResult(False, f"Invalid username: {username}")

        if username.lower() in {"root", "hspanel", "pdns", "mysql"}:
            return ServiceResult(False, f"Cannot delete system user: {username}")

        sql = f"DROP USER IF EXISTS '{username}'@'localhost';"
        rc, _, err = self._mysql(sql)
        _ = self._mysql("FLUSH PRIVILEGES;")
        return ServiceResult(rc == 0, f"DB user deleted: {username}" if rc == 0 else err)

    def grant_privileges(
        self, db_name: str, username: str, privileges: str = "ALL PRIVILEGES"
    ) -> ServiceResult:
        if not self._validate_db_identifier(db_name) or not self._validate_db_identifier(username):
            return ServiceResult(False, "Invalid db_name or username")

        sql = (
            f"GRANT {privileges} ON `{db_name}`.* TO '{username}'@'localhost'; "
            f"FLUSH PRIVILEGES;"
        )
        rc, _, err = self._mysql(sql)
        return ServiceResult(rc == 0, f"Privileges granted on {db_name} to {username}" if rc == 0 else err)

    def change_db_user_password(self, username: str, new_password: str) -> ServiceResult:
        if not self._validate_db_identifier(username):
            return ServiceResult(False, f"Invalid username: {username}")

        sql = (
            f"ALTER USER '{username}'@'localhost' "
            f"IDENTIFIED BY '{self._escape_sql_string(new_password)}'; "
            f"FLUSH PRIVILEGES;"
        )
        rc, _, err = self._mysql(sql)
        return ServiceResult(rc == 0, "Password changed" if rc == 0 else err)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _mysql(self, sql: str) -> tuple[int, str, str]:
        """Execute SQL as root via unix socket (no password prompt in secure environments)."""
        return self._run(
            ["mysql", "--socket", MYSQL_SOCKET, "-u", "root", "-e", sql],
            timeout=30,
        )

    @staticmethod
    def _validate_db_identifier(name: str) -> bool:
        """Only allow safe DB/user names."""
        return bool(re.match(r'^[a-zA-Z0-9_]{1,64}$', name))

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        """Basic SQL string escaping — backtick values are always quoted."""
        return value.replace("'", "\\'").replace("\\", "\\\\")

    @staticmethod
    def _generate_password(length: int = 20) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))
