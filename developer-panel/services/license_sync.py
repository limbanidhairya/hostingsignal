"""License Sync Service — Syncs with the HostingSignal License Server"""
import httpx
import logging
from typing import Optional
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LicenseSyncService:
    """Manages communication with the HostingSignal license server."""

    def __init__(self):
        self.base_url = settings.LICENSE_SERVER_URL
        self.api_key = settings.LICENSE_API_KEY
        # License server authenticates via X-API-Key header (master API key or user API key)
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs):
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, f"{self.base_url}{path}", headers=self.headers, **kwargs)
            resp.raise_for_status()
            return resp.json()

    async def create_license(self, plan: str, domain: str, max_domains: int = 1,
                             expiry_days: int = 365, features: dict = None) -> dict:
        features = features or {}
        customer_email = features.get("customer_email") or f"client@{domain}"
        return await self._request("POST", "/license/create", json={
            "customer_email": customer_email,
            "tier": plan,
            "bound_domain": domain,
            "max_activations": max_domains,
            "expires_days": expiry_days,
            "bound_ip": features.get("ip_binding") or None,
        })

    async def validate_license(self, key: str) -> dict:
        return await self._request("POST", "/license/validate", json={"license_key": key})

    async def revoke_license(self, key: str, reason: str = "") -> dict:
        return await self._request("POST", "/license/revoke", json={"license_key": key, "reason": reason})

    async def get_license_info(self, key: str) -> dict:
        return await self._request("GET", "/license/info", params={"license_key": key})

    async def list_licenses(self, page: int = 1, per_page: int = 50, status: str = None) -> dict:
        offset = (page - 1) * per_page
        params = {"limit": per_page, "offset": offset}
        if status:
            params["status"] = status
        return await self._request("GET", "/license/list", params=params)

    async def get_license_stats(self) -> dict:
        """Compute stats from the license list (no dedicated stats endpoint)."""
        result = await self._request("GET", "/license/list", params={"limit": 200, "offset": 0})
        licenses = result.get("licenses", [])
        total = result.get("count", len(licenses))
        by_status: dict = {}
        by_tier: dict = {}
        for lic in licenses:
            s = lic.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
            t = lic.get("tier", "unknown")
            by_tier[t] = by_tier.get(t, 0) + 1
        return {
            "total": total,
            "active": by_status.get("active", 0),
            "expired": by_status.get("expired", 0),
            "revoked": by_status.get("revoked", 0),
            "suspended": by_status.get("suspended", 0),
            "by_tier": by_tier,
        }

    async def bulk_create(self, count: int, plan: str, expiry_days: int = 365) -> list:
        # Bulk-create by issuing individual create requests
        results = []
        for i in range(count):
            try:
                lic = await self.create_license(
                    plan=plan,
                    domain=f"bulk-{i+1}.example.com",
                    expiry_days=expiry_days,
                    features={"customer_email": f"bulk-{i+1}@example.com"},
                )
                results.append(lic)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Bulk create item %d failed: %s", i + 1, exc)
        return results


license_sync = LicenseSyncService()
