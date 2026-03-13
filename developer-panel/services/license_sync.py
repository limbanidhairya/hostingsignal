"""License Sync Service — Syncs with the license.hostingsignal.com API"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LicenseSyncService:
    """Manages communication with the external license server."""

    def __init__(self):
        self.base_url = settings.LICENSE_SERVER_URL
        self.api_key = settings.LICENSE_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs):
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, f"{self.base_url}{path}", headers=self.headers, **kwargs)
            resp.raise_for_status()
            return resp.json()

    async def create_license(self, plan: str, domain: str, max_domains: int = 1,
                             expiry_days: int = 365, features: dict = None) -> dict:
        return await self._request("POST", "/api/license/create", json={
            "plan": plan,
            "domain": domain,
            "max_domains": max_domains,
            "expiry_date": (datetime.utcnow() + timedelta(days=expiry_days)).isoformat(),
            "features": features or {},
        })

    async def validate_license(self, key: str) -> dict:
        return await self._request("POST", "/api/license/validate", json={"key": key})

    async def revoke_license(self, key: str, reason: str = "") -> dict:
        return await self._request("POST", "/api/license/revoke", json={"key": key, "reason": reason})

    async def get_license_info(self, key: str) -> dict:
        return await self._request("GET", f"/api/license/info?key={key}")

    async def list_licenses(self, page: int = 1, per_page: int = 50, status: str = None) -> dict:
        params = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        return await self._request("GET", "/api/license/list", params=params)

    async def get_license_stats(self) -> dict:
        return await self._request("GET", "/api/license/stats")

    async def bulk_create(self, count: int, plan: str, expiry_days: int = 365) -> list:
        return await self._request("POST", "/api/license/bulk-create", json={
            "count": count,
            "plan": plan,
            "expiry_days": expiry_days,
        })


license_sync = LicenseSyncService()
