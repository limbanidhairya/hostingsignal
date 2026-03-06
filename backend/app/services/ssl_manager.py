"""
HostingSignal — SSL/TLS Manager (Let's Encrypt via certbot)
Issue, renew, revoke SSL certificates.
"""
from .server_utils import run_cmd, DEV_MODE, logger

DEMO_CERTS = [
    {"domain": "example.com", "issuer": "Let's Encrypt", "expires": "2026-05-30", "status": "valid", "auto_renew": True},
    {"domain": "blog.example.com", "issuer": "Let's Encrypt", "expires": "2026-04-15", "status": "valid", "auto_renew": True},
]


def list_certificates() -> list[dict]:
    if DEV_MODE:
        return DEMO_CERTS
    result = run_cmd("certbot certificates 2>/dev/null", timeout=30)
    certs = []
    current = {}
    for line in result.stdout.split("\n"):
        line = line.strip()
        if "Certificate Name:" in line:
            if current:
                certs.append(current)
            current = {"domain": line.split(":")[-1].strip(), "issuer": "Let's Encrypt", "auto_renew": True}
        elif "Expiry Date:" in line:
            current["expires"] = line.split(":")[-1].strip().split(" ")[0] if ":" in line else ""
            current["status"] = "valid" if "VALID" in line.upper() else "expiring"
    if current:
        certs.append(current)
    return certs


def issue_certificate(domain: str, email: str = "admin@hostingsignal.com", wildcard: bool = False) -> dict:
    """Issue a Let's Encrypt certificate."""
    if wildcard:
        cmd = f"certbot certonly --manual --preferred-challenges dns -d '*.{domain}' -d '{domain}' --email {email} --agree-tos --no-eff-email -n"
    else:
        cmd = f"certbot certonly --webroot -w /home/{domain}/public_html -d {domain} -d www.{domain} --email {email} --agree-tos --no-eff-email -n"
    result = run_cmd(cmd, timeout=120)
    if result.success or DEV_MODE:
        # Install cert to OLS
        _install_to_ols(domain)
        return {"domain": domain, "status": "issued", "issuer": "Let's Encrypt", "auto_renew": True}
    return {"domain": domain, "status": "failed", "error": result.stderr}


def renew_certificate(domain: str | None = None) -> dict:
    """Renew a specific certificate or all."""
    if domain:
        cmd = f"certbot renew --cert-name {domain} --force-renewal"
    else:
        cmd = "certbot renew"
    result = run_cmd(cmd, timeout=300)
    return {"status": "renewed" if result.success or DEV_MODE else "failed", "output": result.stdout[:500]}


def revoke_certificate(domain: str) -> dict:
    result = run_cmd(f"certbot revoke --cert-name {domain} --no-delete-after-revoke -n", timeout=60)
    return {"domain": domain, "status": "revoked" if result.success or DEV_MODE else "failed"}


def _install_to_ols(domain: str):
    """Install cert files into OpenLiteSpeed vhost."""
    cert_path = f"/etc/letsencrypt/live/{domain}"
    run_cmd(f"cat {cert_path}/fullchain.pem > /usr/local/lsws/conf/vhosts/{domain}/cert.pem")
    run_cmd(f"cat {cert_path}/privkey.pem > /usr/local/lsws/conf/vhosts/{domain}/key.pem")
    run_cmd("/usr/local/lsws/bin/lswsctrl restart")


def setup_auto_renew() -> dict:
    """Ensure certbot auto-renewal cron is set up."""
    result = run_cmd("systemctl enable --now certbot-renew.timer 2>/dev/null || "
                     "(crontab -l 2>/dev/null; echo '0 3 * * * certbot renew --post-hook \"systemctl restart lsws\"') | sort -u | crontab -")
    return {"status": "enabled", "schedule": "Daily at 3 AM"}
