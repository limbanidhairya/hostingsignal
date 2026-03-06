"""
HostingSignal — System Monitor
CPU, RAM, Disk, Bandwidth, Service status, Uptime.
"""
import platform
from .server_utils import run_cmd, DEV_MODE, logger, service_status_all

DEMO_STATS = {
    "cpu": {"usage_percent": 34, "cores": 4, "model": "Intel Xeon E5-2680 v4", "load": [1.2, 0.9, 0.7]},
    "ram": {"total_mb": 4096, "used_mb": 2560, "free_mb": 1536, "usage_percent": 62},
    "disk": {"total_gb": 50, "used_gb": 22.5, "free_gb": 27.5, "usage_percent": 45},
    "bandwidth": {"total_gb": 1000, "used_gb": 180, "usage_percent": 18},
    "uptime": "14 days, 6 hours, 32 minutes",
    "hostname": "server1.hostingsignal.com",
    "os": "Ubuntu 22.04 LTS",
    "kernel": "5.15.0-91-generic",
}


def get_system_stats() -> dict:
    """Get comprehensive system statistics."""
    if DEV_MODE:
        return DEMO_STATS
    stats = {}

    # CPU
    cpu_result = run_cmd("grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2")
    cores_result = run_cmd("nproc")
    load_result = run_cmd("cat /proc/loadavg")
    cpu_usage = run_cmd("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
    stats["cpu"] = {
        "model": cpu_result.stdout.strip() if cpu_result.success else "Unknown",
        "cores": int(cores_result.stdout.strip()) if cores_result.success else 1,
        "usage_percent": float(cpu_usage.stdout.strip()) if cpu_usage.success else 0,
        "load": [float(x) for x in load_result.stdout.split()[:3]] if load_result.success else [0, 0, 0],
    }

    # RAM
    mem_result = run_cmd("free -m | grep Mem")
    if mem_result.success:
        parts = mem_result.stdout.split()
        total = int(parts[1])
        used = int(parts[2])
        stats["ram"] = {
            "total_mb": total,
            "used_mb": used,
            "free_mb": total - used,
            "usage_percent": round(used / total * 100) if total > 0 else 0,
        }
    else:
        stats["ram"] = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "usage_percent": 0}

    # Disk
    disk_result = run_cmd("df -BG / | tail -1")
    if disk_result.success:
        parts = disk_result.stdout.split()
        total = float(parts[1].rstrip("G"))
        used = float(parts[2].rstrip("G"))
        stats["disk"] = {
            "total_gb": total,
            "used_gb": used,
            "free_gb": total - used,
            "usage_percent": round(used / total * 100) if total > 0 else 0,
        }
    else:
        stats["disk"] = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "usage_percent": 0}

    # Bandwidth (approximation via vnstat or net counters)
    bw_result = run_cmd("vnstat --json m 2>/dev/null || echo '{}'")
    stats["bandwidth"] = {"total_gb": 1000, "used_gb": 0, "usage_percent": 0}

    # Uptime
    uptime_result = run_cmd("uptime -p")
    stats["uptime"] = uptime_result.stdout.strip().replace("up ", "") if uptime_result.success else "Unknown"

    # System info
    stats["hostname"] = platform.node()
    os_result = run_cmd("cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'")
    stats["os"] = os_result.stdout.strip() if os_result.success else platform.platform()
    kernel_result = run_cmd("uname -r")
    stats["kernel"] = kernel_result.stdout.strip() if kernel_result.success else platform.release()

    return stats


def get_service_statuses() -> list[dict]:
    """Get status of all managed services."""
    return service_status_all()


def get_process_list(limit: int = 20) -> list[dict]:
    """Get top processes by CPU usage."""
    if DEV_MODE:
        return [
            {"pid": 1234, "user": "root", "cpu": 12.5, "mem": 4.2, "command": "lshttpd"},
            {"pid": 2345, "user": "mysql", "cpu": 8.1, "mem": 15.3, "command": "mariadbd"},
            {"pid": 3456, "user": "root", "cpu": 2.3, "mem": 1.1, "command": "pdns_server"},
        ]
    result = run_cmd(f"ps aux --sort=-%cpu | head -n {limit + 1}")
    processes = []
    if result.success:
        for line in result.stdout.split("\n")[1:]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                processes.append({
                    "pid": int(parts[1]),
                    "user": parts[0],
                    "cpu": float(parts[2]),
                    "mem": float(parts[3]),
                    "command": parts[10][:60],
                })
    return processes
