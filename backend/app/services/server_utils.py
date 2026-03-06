"""
HostingSignal — Core Server Utilities
OS detection, command execution, service management, dev-mode fallbacks.
"""
import os
import platform
import subprocess
import shutil
import logging

logger = logging.getLogger("hostingsignal.server")

# ---------------------------------------------------------------------------
# Dev-mode detection
# ---------------------------------------------------------------------------
IS_LINUX = platform.system() == "Linux"
DEV_MODE = os.getenv("HS_DEV_MODE", "0") == "1" or not IS_LINUX


def get_os_info() -> dict:
    """Detect the operating system family and version."""
    if DEV_MODE:
        return {
            "os": "Ubuntu", "version": "22.04", "codename": "jammy",
            "family": "debian", "arch": platform.machine(),
            "dev_mode": True,
        }
    info = {"os": "Unknown", "version": "", "codename": "", "family": "unknown",
            "arch": platform.machine(), "dev_mode": False}
    try:
        with open("/etc/os-release") as f:
            lines = {k: v.strip('"') for line in f for k, _, v in [line.strip().partition("=")]}
        info["os"] = lines.get("NAME", "Unknown")
        info["version"] = lines.get("VERSION_ID", "")
        info["codename"] = lines.get("VERSION_CODENAME", "")
        name_lower = info["os"].lower()
        if "ubuntu" in name_lower or "debian" in name_lower:
            info["family"] = "debian"
        elif any(x in name_lower for x in ("alma", "centos", "rocky", "rhel", "red hat")):
            info["family"] = "rhel"
        else:
            info["family"] = "unknown"
    except FileNotFoundError:
        pass
    return info


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------
class CommandResult:
    """Wrapper for subprocess results."""
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.success = returncode == 0

    def __repr__(self):
        return f"CommandResult(rc={self.returncode}, success={self.success})"


def run_cmd(cmd: str | list, timeout: int = 60, check: bool = False,
            shell: bool = True, cwd: str | None = None) -> CommandResult:
    """
    Run a system command. In DEV_MODE returns a fake success result.
    """
    if DEV_MODE:
        logger.info(f"[DEV] Would run: {cmd}")
        return CommandResult(0, f"[dev-mode] {cmd}", "")
    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
        )
        if check and result.returncode != 0:
            logger.error(f"Command failed: {cmd}\nstderr: {result.stderr}")
        return CommandResult(result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return CommandResult(-1, "", f"Command timed out after {timeout}s")
    except Exception as e:
        return CommandResult(-1, "", str(e))


# ---------------------------------------------------------------------------
# Service management (systemctl)
# ---------------------------------------------------------------------------
SERVICES = {
    "openlitespeed": "lsws",
    "webserver": "lsws",
    "dns": "pdns",
    "powerdns": "pdns",
    "postfix": "postfix",
    "dovecot": "dovecot",
    "mariadb": "mariadb",
    "mysql": "mariadb",
    "pureftpd": "pure-ftpd",
    "ftp": "pure-ftpd",
    "firewalld": "firewalld",
    "docker": "docker",
}


def _resolve_service(name: str) -> str:
    return SERVICES.get(name.lower(), name)


def service_action(name: str, action: str) -> CommandResult:
    """Start / stop / restart / reload / status a systemd service."""
    svc = _resolve_service(name)
    return run_cmd(f"systemctl {action} {svc}")


def service_status(name: str) -> dict:
    """Return structured status of a service."""
    svc = _resolve_service(name)
    if DEV_MODE:
        return {"name": svc, "active": True, "running": True, "enabled": True, "dev_mode": True}
    result = run_cmd(f"systemctl is-active {svc}")
    is_active = result.stdout.strip() == "active"
    result_e = run_cmd(f"systemctl is-enabled {svc}")
    is_enabled = result_e.stdout.strip() == "enabled"
    return {"name": svc, "active": is_active, "running": is_active, "enabled": is_enabled}


def service_status_all() -> list[dict]:
    """Return status of all managed services."""
    return [service_status(svc) for svc in [
        "openlitespeed", "dns", "postfix", "dovecot",
        "mariadb", "pureftpd", "firewalld", "docker",
    ]]


# ---------------------------------------------------------------------------
# Package manager helpers
# ---------------------------------------------------------------------------
def install_packages(packages: list[str]) -> CommandResult:
    """Install packages using the detected package manager."""
    os_info = get_os_info()
    if os_info["family"] == "debian":
        cmd = f"apt-get install -y {' '.join(packages)}"
    elif os_info["family"] == "rhel":
        cmd = f"dnf install -y {' '.join(packages)}"
    else:
        return CommandResult(-1, "", f"Unsupported OS family: {os_info['family']}")
    return run_cmd(cmd, timeout=300)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def read_file(path: str) -> str | None:
    if DEV_MODE:
        return f"[dev-mode] contents of {path}"
    try:
        with open(path) as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def write_file(path: str, content: str, backup: bool = True) -> bool:
    if DEV_MODE:
        logger.info(f"[DEV] Would write to {path} ({len(content)} bytes)")
        return True
    try:
        if backup and os.path.exists(path):
            shutil.copy2(path, path + ".bak")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")
        return False


def ensure_dir(path: str) -> bool:
    if DEV_MODE:
        return True
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------
def get_server_ip() -> str:
    """Detect the server's public IP."""
    if DEV_MODE:
        return "127.0.0.1"
    result = run_cmd("curl -4 -s ifconfig.me", timeout=10)
    if result.success and result.stdout.strip():
        return result.stdout.strip()
    result = run_cmd("hostname -I | awk '{print $1}'", timeout=5)
    return result.stdout.strip() if result.success else "0.0.0.0"


def get_hostname() -> str:
    if DEV_MODE:
        return "dev.hostingsignal.local"
    result = run_cmd("hostname -f", timeout=5)
    return result.stdout.strip() if result.success else platform.node()
