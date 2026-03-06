"""
HostingSignal — MariaDB Database Manager
Create/delete databases and users, manage privileges, import/export.
"""
from .server_utils import run_cmd, DEV_MODE, logger
import secrets, string

DEMO_DATABASES = [
    {"name": "wp_example", "user": "wp_user", "size": "24.5 MB", "tables": 12},
    {"name": "app_store", "user": "store_user", "size": "156.2 MB", "tables": 34},
    {"name": "analytics_db", "user": "analytics", "size": "512.8 MB", "tables": 8},
]


def _mysql_cmd(sql: str) -> str:
    """Execute a MySQL command and return output."""
    if DEV_MODE:
        logger.info(f"[DEV] MySQL: {sql[:80]}...")
        return "[dev-mode] OK"
    result = run_cmd(f'mysql -e "{sql}"', timeout=30)
    return result.stdout if result.success else result.stderr


def list_databases() -> list[dict]:
    """List all user databases (excluding system DBs)."""
    if DEV_MODE:
        return DEMO_DATABASES
    output = _mysql_cmd("SELECT table_schema AS db, ROUND(SUM(data_length+index_length)/1024/1024, 1) AS size_mb, COUNT(*) AS tables FROM information_schema.tables WHERE table_schema NOT IN ('mysql','information_schema','performance_schema','sys') GROUP BY table_schema;")
    dbs = []
    for line in output.strip().split("\n")[1:]:  # Skip header
        parts = line.split("\t")
        if len(parts) >= 3:
            dbs.append({"name": parts[0], "size": f"{parts[1]} MB", "tables": int(parts[2])})
    return dbs


def create_database(db_name: str, username: str | None = None, password: str | None = None) -> dict:
    """Create a database and optional user with full privileges."""
    if not username:
        username = f"{db_name}_user"
    if not password:
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    _mysql_cmd(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    _mysql_cmd(f"CREATE USER IF NOT EXISTS '{username}'@'localhost' IDENTIFIED BY '{password}';")
    _mysql_cmd(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'localhost';")
    _mysql_cmd("FLUSH PRIVILEGES;")

    return {"name": db_name, "user": username, "password": password, "host": "localhost", "size": "0 MB", "tables": 0}


def delete_database(db_name: str, drop_user: str | None = None) -> bool:
    """Drop a database and optionally its user."""
    _mysql_cmd(f"DROP DATABASE IF EXISTS `{db_name}`;")
    if drop_user:
        _mysql_cmd(f"DROP USER IF EXISTS '{drop_user}'@'localhost';")
        _mysql_cmd("FLUSH PRIVILEGES;")
    return True


def create_user(username: str, password: str, db_name: str | None = None) -> dict:
    """Create a database user with optional database access."""
    _mysql_cmd(f"CREATE USER IF NOT EXISTS '{username}'@'localhost' IDENTIFIED BY '{password}';")
    if db_name:
        _mysql_cmd(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'localhost';")
    _mysql_cmd("FLUSH PRIVILEGES;")
    return {"user": username, "host": "localhost", "database": db_name}


def delete_user(username: str) -> bool:
    _mysql_cmd(f"DROP USER IF EXISTS '{username}'@'localhost';")
    _mysql_cmd("FLUSH PRIVILEGES;")
    return True


def change_user_password(username: str, new_password: str) -> bool:
    _mysql_cmd(f"ALTER USER '{username}'@'localhost' IDENTIFIED BY '{new_password}';")
    _mysql_cmd("FLUSH PRIVILEGES;")
    return True


def export_database(db_name: str, output_path: str) -> dict:
    """Export a database to SQL file."""
    result = run_cmd(f"mysqldump --single-transaction {db_name} > {output_path}", timeout=300)
    return {"success": result.success, "path": output_path}


def import_database(db_name: str, sql_path: str) -> dict:
    """Import SQL file into a database."""
    result = run_cmd(f"mysql {db_name} < {sql_path}", timeout=300)
    return {"success": result.success}


def database_size(db_name: str) -> str:
    """Get database size."""
    if DEV_MODE:
        return "24.5 MB"
    output = _mysql_cmd(f"SELECT ROUND(SUM(data_length+index_length)/1024/1024, 1) FROM information_schema.tables WHERE table_schema='{db_name}';")
    lines = output.strip().split("\n")
    return f"{lines[-1].strip()} MB" if len(lines) > 1 else "0 MB"
