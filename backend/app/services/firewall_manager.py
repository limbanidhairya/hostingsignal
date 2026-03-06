"""
HostingSignal — FirewallD Manager
Manage firewall rules, ports, IP blocking, and zones.
"""
from .server_utils import run_cmd, DEV_MODE, logger

DEMO_RULES = [
    {"port": "22/tcp", "service": "SSH", "zone": "public", "status": "open"},
    {"port": "80/tcp", "service": "HTTP", "zone": "public", "status": "open"},
    {"port": "443/tcp", "service": "HTTPS", "zone": "public", "status": "open"},
    {"port": "8088/tcp", "service": "OLS Admin", "zone": "public", "status": "open"},
    {"port": "8090/tcp", "service": "HostingSignal", "zone": "public", "status": "open"},
    {"port": "3306/tcp", "service": "MariaDB", "zone": "public", "status": "closed"},
]

DEMO_BLOCKED = [
    {"ip": "192.168.1.50", "reason": "Brute-force SSH", "date": "2026-02-28"},
    {"ip": "10.0.0.99", "reason": "DDoS attempt", "date": "2026-02-27"},
]


def list_rules() -> list[dict]:
    if DEV_MODE:
        return DEMO_RULES
    result = run_cmd("firewall-cmd --list-all --zone=public")
    rules = []
    if result.success:
        for line in result.stdout.split("\n"):
            if "ports:" in line:
                ports = line.split(":")[-1].strip().split()
                for p in ports:
                    rules.append({"port": p, "zone": "public", "status": "open"})
    return rules


def open_port(port: int, protocol: str = "tcp", zone: str = "public") -> dict:
    run_cmd(f"firewall-cmd --zone={zone} --add-port={port}/{protocol} --permanent")
    run_cmd("firewall-cmd --reload")
    return {"port": f"{port}/{protocol}", "zone": zone, "status": "open"}


def close_port(port: int, protocol: str = "tcp", zone: str = "public") -> dict:
    run_cmd(f"firewall-cmd --zone={zone} --remove-port={port}/{protocol} --permanent")
    run_cmd("firewall-cmd --reload")
    return {"port": f"{port}/{protocol}", "zone": zone, "status": "closed"}


def block_ip(ip: str, reason: str = "") -> dict:
    run_cmd(f"firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address={ip} reject'")
    run_cmd("firewall-cmd --reload")
    return {"ip": ip, "reason": reason, "status": "blocked"}


def unblock_ip(ip: str) -> dict:
    run_cmd(f"firewall-cmd --permanent --remove-rich-rule='rule family=ipv4 source address={ip} reject'")
    run_cmd("firewall-cmd --reload")
    return {"ip": ip, "status": "unblocked"}


def list_blocked_ips() -> list[dict]:
    if DEV_MODE:
        return DEMO_BLOCKED
    result = run_cmd("firewall-cmd --list-rich-rules")
    blocked = []
    if result.success:
        for line in result.stdout.split("\n"):
            if "reject" in line and "source" in line:
                parts = line.split("address=")
                if len(parts) > 1:
                    ip = parts[1].split('"')[1] if '"' in parts[1] else parts[1].split()[0]
                    blocked.append({"ip": ip, "reason": "Firewall rule"})
    return blocked


def firewall_status() -> dict:
    if DEV_MODE:
        return {"active": True, "default_zone": "public", "rules_count": len(DEMO_RULES), "blocked_ips": len(DEMO_BLOCKED)}
    result = run_cmd("firewall-cmd --state")
    active = "running" in result.stdout.lower() if result.success else False
    zone_result = run_cmd("firewall-cmd --get-default-zone")
    return {"active": active, "default_zone": zone_result.stdout.strip() if zone_result.success else "public"}
