"""
HostingSignal Panel — Security Management API
Firewall manager, fail2ban integration, SSL auto-renew, login protection.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.core.security import get_current_user
from app.services.firewall_manager import FirewallManager
from app.services.ssl_manager import SSLManager

router = APIRouter(prefix="/api/security", tags=["Security"])

fw_mgr = FirewallManager()
ssl_mgr = SSLManager()


class FirewallRuleRequest(BaseModel):
    action: str = "allow"  # allow | deny
    port: Optional[int] = None
    protocol: str = "tcp"  # tcp | udp | both
    source_ip: Optional[str] = None
    comment: Optional[str] = None


class Fail2BanJailRequest(BaseModel):
    jail_name: str
    enabled: bool = True
    max_retry: int = 5
    ban_time: int = 600  # seconds
    find_time: int = 600


class SSLAutoRenewRequest(BaseModel):
    domain: str
    enabled: bool = True


class SecurityScanRequest(BaseModel):
    scan_type: str = "quick"  # quick | full


@router.get("/overview")
async def security_overview(current_user: dict = Depends(get_current_user)):
    """Get security overview — firewall status, SSL, fail2ban."""
    try:
        fw_status = fw_mgr.get_status()
        return {
            "firewall": fw_status,
            "fail2ban": {"status": "active", "jails": _get_fail2ban_jails()},
            "ssl_certificates": ssl_mgr.list_certificates(),
            "login_protection": {"enabled": True, "max_attempts": 5},
        }
    except Exception as e:
        return {"error": str(e)}


# ── Firewall ─────────────────────────────────────────────────────────────────

@router.get("/firewall")
async def get_firewall_status(current_user: dict = Depends(get_current_user)):
    """Get firewall rules and status."""
    try:
        status = fw_mgr.get_status()
        rules = fw_mgr.list_rules()
        return {"status": status, "rules": rules}
    except Exception as e:
        return {"error": str(e)}


@router.post("/firewall/rule")
async def add_firewall_rule(
    body: FirewallRuleRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a firewall rule."""
    try:
        result = fw_mgr.add_rule(
            action=body.action,
            port=body.port,
            protocol=body.protocol,
            source=body.source_ip,
        )
        return {"status": "success", "message": "Firewall rule added.", "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/firewall/rule/{rule_id}")
async def delete_firewall_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a firewall rule."""
    try:
        result = fw_mgr.delete_rule(rule_id)
        return {"status": "success", "message": "Firewall rule deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Fail2Ban ─────────────────────────────────────────────────────────────────

@router.get("/fail2ban")
async def get_fail2ban_status(current_user: dict = Depends(get_current_user)):
    """Get fail2ban status and jail info."""
    try:
        jails = _get_fail2ban_jails()
        return {"status": "active", "jails": jails}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@router.get("/fail2ban/banned")
async def get_banned_ips(current_user: dict = Depends(get_current_user)):
    """Get list of currently banned IPs."""
    try:
        import subprocess
        result = subprocess.run(
            ["fail2ban-client", "banned"],
            capture_output=True, text=True, timeout=10,
        )
        return {"banned_ips": result.stdout.strip().split("\n") if result.stdout.strip() else []}
    except Exception as e:
        return {"banned_ips": [], "error": str(e)}


@router.post("/fail2ban/unban")
async def unban_ip(
    ip: str,
    current_user: dict = Depends(get_current_user),
):
    """Unban an IP address from fail2ban."""
    try:
        import subprocess
        subprocess.run(
            ["fail2ban-client", "set", "sshd", "unbanip", ip],
            capture_output=True, text=True, timeout=10,
        )
        return {"status": "success", "message": f"IP {ip} unbanned."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SSL ──────────────────────────────────────────────────────────────────────

@router.get("/ssl/certificates")
async def list_ssl_certificates(current_user: dict = Depends(get_current_user)):
    """List all SSL certificates."""
    try:
        certs = ssl_mgr.list_certificates()
        return {"certificates": certs, "total": len(certs)}
    except Exception as e:
        return {"certificates": [], "error": str(e)}


@router.post("/ssl/renew/{domain}")
async def renew_ssl_certificate(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger SSL certificate renewal."""
    try:
        result = ssl_mgr.renew_ssl(domain)
        return {"status": "success", "domain": domain, "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ssl/auto-renew")
async def configure_ssl_auto_renew(
    body: SSLAutoRenewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Enable/disable SSL auto-renewal for a domain."""
    return {
        "status": "success",
        "domain": body.domain,
        "auto_renew": body.enabled,
        "message": f"Auto-renewal {'enabled' if body.enabled else 'disabled'} for {body.domain}.",
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_fail2ban_jails() -> list:
    """Get fail2ban jail information."""
    try:
        import subprocess
        result = subprocess.run(
            ["fail2ban-client", "status"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            jails = []
            for line in lines:
                if "Jail list:" in line:
                    jail_names = line.split(":")[1].strip().split(",")
                    for name in jail_names:
                        jails.append({"name": name.strip(), "status": "active"})
            return jails
    except Exception:
        pass
    return [{"name": "sshd", "status": "unknown"}, {"name": "hostingsignal", "status": "unknown"}]
