"""
HostingSignal — FTP Manager (Pure-FTPd)
Create/manage FTP accounts.
"""
from .server_utils import run_cmd, DEV_MODE, logger

DEMO_FTP_ACCOUNTS = [
    {"user": "ftp_example", "directory": "/home/example.com/public_html", "status": "active", "quota": "unlimited"},
    {"user": "ftp_blog", "directory": "/home/blog.example.com/public_html", "status": "active", "quota": "5000MB"},
]


def list_accounts() -> list[dict]:
    if DEV_MODE:
        return DEMO_FTP_ACCOUNTS
    result = run_cmd("pure-pw list 2>/dev/null || cat /etc/pureftpd.passwd 2>/dev/null")
    accounts = []
    if result.success:
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if parts:
                accounts.append({"user": parts[0], "directory": parts[5] if len(parts) > 5 else "/home", "status": "active"})
    return accounts


def create_account(username: str, password: str, directory: str, quota_mb: int = 0) -> dict:
    """Create a new FTP account."""
    quota_flag = f"-N {quota_mb}" if quota_mb > 0 else ""
    run_cmd(f"(echo '{password}'; echo '{password}') | pure-pw useradd {username} -u www-data -g www-data -d {directory} {quota_flag}")
    run_cmd("pure-pw mkdb")
    return {"user": username, "directory": directory, "status": "active",
            "quota": f"{quota_mb}MB" if quota_mb > 0 else "unlimited"}


def delete_account(username: str) -> bool:
    run_cmd(f"pure-pw userdel {username}")
    run_cmd("pure-pw mkdb")
    return True


def change_password(username: str, new_password: str) -> bool:
    run_cmd(f"(echo '{new_password}'; echo '{new_password}') | pure-pw passwd {username}")
    run_cmd("pure-pw mkdb")
    return True


def set_quota(username: str, quota_mb: int) -> bool:
    run_cmd(f"pure-pw usermod {username} -N {quota_mb}")
    run_cmd("pure-pw mkdb")
    return True


def set_directory(username: str, directory: str) -> bool:
    run_cmd(f"pure-pw usermod {username} -d {directory}")
    run_cmd("pure-pw mkdb")
    return True
