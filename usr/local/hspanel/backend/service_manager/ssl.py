"""
service_manager/ssl.py — Let's Encrypt SSL certificate manager via certbot
Issues, renews, revokes, and lists certificates for panel domains.
"""
from __future__ import annotations

import re
import os
import json
import logging
from pathlib import Path
from datetime import datetime

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

CERTBOT_BIN     = "/usr/bin/certbot"
WEBROOT_PATH    = "/var/www/letsencrypt"
LE_CERTS_DIR    = "/etc/letsencrypt/live"
LE_RENEWAL_DIR  = "/etc/letsencrypt/renewal"
PANEL_SSL_DIR   = "/usr/local/hspanel/config/ssl"


class SSLManager(BaseServiceManager):
    """Manage SSL certificates using Let's Encrypt / certbot."""

    # ------------------------------------------------------------------
    # Certificate issuance
    # ------------------------------------------------------------------
    def issue_cert(
        self,
        domain: str,
        admin_email: str,
        webroot: str = WEBROOT_PATH,
        staging: bool = False,
    ) -> ServiceResult:
        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain: {domain}")

        if not self._validate_email(admin_email):
            return ServiceResult(False, f"Invalid email: {admin_email}")

        if not Path(CERTBOT_BIN).exists():
            return ServiceResult(False, f"certbot not found at {CERTBOT_BIN}")

        # Ensure webroot exists
        Path(webroot).mkdir(parents=True, exist_ok=True)

        cmd = [
            CERTBOT_BIN, "certonly",
            "--webroot",
            f"--webroot-path={webroot}",
            "--non-interactive",
            "--agree-tos",
            f"--email={admin_email}",
            "--domains", domain,
            "--domains", f"www.{domain}",
            "--cert-name", domain,
        ]
        if staging:
            cmd.append("--staging")

        rc, out, err = self._run(cmd, timeout=120)
        if rc == 0:
            cert_path = f"{LE_CERTS_DIR}/{domain}"
            return ServiceResult(
                True,
                f"SSL certificate issued for {domain}",
                {
                    "domain": domain,
                    "cert": f"{cert_path}/fullchain.pem",
                    "key": f"{cert_path}/privkey.pem",
                },
            )
        return ServiceResult(False, f"certbot failed: {(err or out)[:400]}")

    def renew_cert(self, domain: str | None = None) -> ServiceResult:
        cmd = [CERTBOT_BIN, "renew", "--non-interactive", "--quiet"]
        if domain:
            cmd += ["--cert-name", domain]
        rc, out, err = self._run(cmd, timeout=180)
        return ServiceResult(rc == 0, out or err or "Renewal complete")

    def revoke_cert(self, domain: str) -> ServiceResult:
        cert_file = f"{LE_CERTS_DIR}/{domain}/cert.pem"
        if not Path(cert_file).exists():
            return ServiceResult(False, f"Certificate not found for {domain}")

        cmd = [CERTBOT_BIN, "revoke", "--cert-path", cert_file,
               "--non-interactive", "--quiet"]
        rc, out, err = self._run(cmd, timeout=60)
        return ServiceResult(rc == 0, out or err or f"Certificate revoked: {domain}")

    # ------------------------------------------------------------------
    # Certificate inspection
    # ------------------------------------------------------------------
    def list_certs(self) -> list[dict]:
        certs = []
        live_dir = Path(LE_CERTS_DIR)
        if not live_dir.exists():
            return certs

        for cert_dir in live_dir.iterdir():
            if not cert_dir.is_dir():
                continue
            info = self._cert_info(cert_dir.name)
            if info:
                certs.append(info)
        return certs

    def get_cert_info(self, domain: str) -> dict | None:
        return self._cert_info(domain)

    def _cert_info(self, domain: str) -> dict | None:
        cert_path = Path(f"{LE_CERTS_DIR}/{domain}/cert.pem")
        if not cert_path.exists():
            return None

        rc, out, _ = self._run(
            ["openssl", "x509", "-in", str(cert_path), "-noout",
             "-dates", "-subject", "-issuer"],
            timeout=5,
        )
        info: dict = {"domain": domain, "cert": str(cert_path)}
        if rc == 0:
            for line in out.splitlines():
                if line.startswith("notAfter="):
                    expiry_str = line.split("=", 1)[1].strip()
                    try:
                        expiry = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                        info["expires"] = expiry.isoformat()
                        info["days_remaining"] = (expiry - datetime.utcnow()).days
                        info["valid"] = info["days_remaining"] > 0
                    except ValueError:
                        pass
                elif line.startswith("subject="):
                    info["subject"] = line.split("=", 1)[1].strip()
        return info

    # ------------------------------------------------------------------
    # Panel self-signed cert (for panel HTTPS)
    # ------------------------------------------------------------------
    def generate_self_signed(self, hostname: str | None = None) -> ServiceResult:
        hostname = hostname or "hspanel.localhost"
        Path(PANEL_SSL_DIR).mkdir(parents=True, exist_ok=True)
        cert_out = f"{PANEL_SSL_DIR}/panel.crt"
        key_out  = f"{PANEL_SSL_DIR}/panel.key"

        cmd = [
            "openssl", "req", "-newkey", "rsa:2048", "-nodes",
            "-keyout", key_out,
            "-x509", "-days", "3650",
            "-out", cert_out,
            "-subj", f"/CN={hostname}/O=HS-Panel/C=US",
        ]
        rc, out, err = self._run(cmd, timeout=30)
        if rc == 0:
            os.chmod(key_out, 0o640)
            return ServiceResult(
                True,
                f"Self-signed certificate generated for {hostname}",
                {"cert": cert_out, "key": key_out},
            )
        return ServiceResult(False, f"openssl failed: {err}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_domain(domain: str) -> bool:
        return bool(re.match(r'^(?!-)[A-Za-z0-9\-]{1,63}(?<!-)(\.[A-Za-z0-9\-]{1,63})+$', domain))

    @staticmethod
    def _validate_email(email: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))
