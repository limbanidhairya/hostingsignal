"""
service_manager/dns.py — PowerDNS zone and record manager
Uses PowerDNS HTTP API (localhost:8053) for all operations.
"""
from __future__ import annotations

import re
import logging
from typing import Any
from pathlib import Path

import httpx

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

PDNS_API_URL     = "http://127.0.0.1:8053/api/v1"
PDNS_CONF_FILE   = "/etc/powerdns/pdns.conf"
PDNS_SERVER_ID   = "localhost"
DEFAULT_TTL      = 300
DEFAULT_NS1      = "ns1.yourdomain.com"
DEFAULT_NS2      = "ns2.yourdomain.com"

# Allowed DNS record types
ALLOWED_RECORD_TYPES = {
    "A", "AAAA", "CNAME", "MX", "NS", "TXT", "SRV",
    "CAA", "PTR", "SOA", "SPF",
}


class DNSManager(BaseServiceManager):
    """Manage PowerDNS zones and records via the PDNS HTTP API."""

    def __init__(self) -> None:
        super().__init__()
        self._api_key = self._read_api_key()

    # ------------------------------------------------------------------
    # Service control
    # ------------------------------------------------------------------
    def reload(self) -> ServiceResult:
        rc, out, err = self._sysop("reload_pdns")
        return ServiceResult(rc == 0, out or err)

    def status(self) -> dict:
        return self.service_status("pdns")

    # ------------------------------------------------------------------
    # Zone management
    # ------------------------------------------------------------------
    def create_zone(
        self,
        domain: str,
        ns1: str = DEFAULT_NS1,
        ns2: str = DEFAULT_NS2,
        admin_email: str = "",
        server_ip: str = "",
    ) -> ServiceResult:
        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain: {domain}")

        fqdn = self._ensure_dot(domain)
        admin = self._ensure_dot(admin_email.replace("@", ".")) if admin_email else f"hostmaster.{fqdn}"

        payload: dict[str, Any] = {
            "name": fqdn,
            "kind": "Native",
            "nameservers": [self._ensure_dot(ns1), self._ensure_dot(ns2)],
            "rrsets": [
                self._make_rrset(fqdn, "NS", DEFAULT_TTL, [
                    {"content": self._ensure_dot(ns1)},
                    {"content": self._ensure_dot(ns2)},
                ]),
                self._make_rrset(fqdn, "SOA", DEFAULT_TTL, [{
                    "content": (
                        f"{self._ensure_dot(ns1)} {admin} "
                        f"{self._serial()} 10800 3600 604800 {DEFAULT_TTL}"
                    )
                }]),
            ],
        }

        if server_ip:
            payload["rrsets"].append(
                self._make_rrset(fqdn, "A", DEFAULT_TTL, [{"content": server_ip}])
            )
            payload["rrsets"].append(
                self._make_rrset(f"www.{fqdn}", "A", DEFAULT_TTL, [{"content": server_ip}])
            )

        resp = self._api_post(f"/servers/{PDNS_SERVER_ID}/zones", payload)
        if resp is None:
            return ServiceResult(False, "PowerDNS API unreachable")
        if resp.status_code in (200, 201):
            return ServiceResult(True, f"DNS zone created: {domain}", {"domain": domain})
        return ServiceResult(False, f"PDNS error: {resp.status_code} — {resp.text[:200]}")

    def delete_zone(self, domain: str) -> ServiceResult:
        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain: {domain}")
        fqdn = self._ensure_dot(domain)
        resp = self._api_delete(f"/servers/{PDNS_SERVER_ID}/zones/{fqdn}")
        if resp is None:
            return ServiceResult(False, "PowerDNS API unreachable")
        if resp.status_code == 204:
            return ServiceResult(True, f"Zone deleted: {domain}")
        return ServiceResult(False, f"PDNS error: {resp.status_code} — {resp.text[:200]}")

    def list_zones(self) -> list[dict]:
        resp = self._api_get(f"/servers/{PDNS_SERVER_ID}/zones")
        if resp is None or resp.status_code != 200:
            return []
        return resp.json()

    def get_zone(self, domain: str) -> dict | None:
        fqdn = self._ensure_dot(domain)
        resp = self._api_get(f"/servers/{PDNS_SERVER_ID}/zones/{fqdn}")
        if resp is None or resp.status_code != 200:
            return None
        return resp.json()

    # ------------------------------------------------------------------
    # Record management
    # ------------------------------------------------------------------
    def add_record(
        self,
        domain: str,
        name: str,
        record_type: str,
        content: str,
        ttl: int = DEFAULT_TTL,
    ) -> ServiceResult:
        record_type = record_type.upper()
        if record_type not in ALLOWED_RECORD_TYPES:
            return ServiceResult(False, f"Unsupported record type: {record_type}")

        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain: {domain}")

        fqdn = self._ensure_dot(domain)
        rec_name = self._ensure_dot(name) if name else fqdn

        payload = {
            "rrsets": [
                {
                    "name": rec_name,
                    "type": record_type,
                    "ttl": ttl,
                    "changetype": "REPLACE",
                    "records": [{"content": content, "disabled": False}],
                }
            ]
        }
        resp = self._api_patch(f"/servers/{PDNS_SERVER_ID}/zones/{fqdn}", payload)
        if resp is None:
            return ServiceResult(False, "PowerDNS API unreachable")
        if resp.status_code == 204:
            return ServiceResult(True, f"Record added: {name} {record_type} {content}")
        return ServiceResult(False, f"PDNS error: {resp.status_code} — {resp.text[:200]}")

    def delete_record(
        self, domain: str, name: str, record_type: str
    ) -> ServiceResult:
        record_type = record_type.upper()
        fqdn = self._ensure_dot(domain)
        rec_name = self._ensure_dot(name) if name else fqdn
        payload = {
            "rrsets": [{"name": rec_name, "type": record_type, "changetype": "DELETE"}]
        }
        resp = self._api_patch(f"/servers/{PDNS_SERVER_ID}/zones/{fqdn}", payload)
        if resp is None:
            return ServiceResult(False, "PowerDNS API unreachable")
        if resp.status_code == 204:
            return ServiceResult(True, f"Record deleted: {name} {record_type}")
        return ServiceResult(False, f"PDNS error: {resp.status_code} — {resp.text[:200]}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _api_get(self, path: str) -> httpx.Response | None:
        return self._api_call("GET", path)

    def _api_post(self, path: str, payload: dict) -> httpx.Response | None:
        return self._api_call("POST", path, payload)

    def _api_patch(self, path: str, payload: dict) -> httpx.Response | None:
        return self._api_call("PATCH", path, payload)

    def _api_delete(self, path: str) -> httpx.Response | None:
        return self._api_call("DELETE", path)

    def _api_call(
        self, method: str, path: str, payload: dict | None = None
    ) -> httpx.Response | None:
        url = f"{PDNS_API_URL}{path}"
        headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.request(method, url, json=payload, headers=headers)
                return resp
        except Exception as exc:  # noqa: BLE001
            logger.error("PowerDNS API call failed: %s — %s", url, exc)
            return None

    def _read_api_key(self) -> str:
        conf = Path(PDNS_CONF_FILE)
        if conf.exists():
            for line in conf.read_text().splitlines():
                if line.startswith("api-key="):
                    return line.split("=", 1)[1].strip()
        return ""

    @staticmethod
    def _ensure_dot(name: str) -> str:
        return name if name.endswith(".") else f"{name}."

    @staticmethod
    def _serial() -> str:
        from datetime import datetime
        return datetime.utcnow().strftime("%Y%m%d01")

    @staticmethod
    def _make_rrset(name: str, rtype: str, ttl: int, records: list[dict]) -> dict:
        return {
            "name": name,
            "type": rtype,
            "ttl": ttl,
            "changetype": "REPLACE",
            "records": [{"content": r["content"], "disabled": False} for r in records],
        }

    @staticmethod
    def _validate_domain(domain: str) -> bool:
        return bool(re.match(r'^(?!-)[A-Za-z0-9\-]{1,63}(?<!-)(\.[A-Za-z0-9\-]{1,63})+$', domain))
