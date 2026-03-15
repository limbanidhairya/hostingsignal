#!/usr/bin/env python3
"""Distributed license client with local cache and grace-period failover."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


ISO_FMT_HINT = "Use ISO-8601 timestamps with timezone, e.g. 2027-01-01T00:00:00+00:00"


@dataclass
class LicenseClientConfig:
    base_url: str
    validate_path: str
    cache_file: Path
    grace_hours: int = 72


class LicenseClient:
    def __init__(self, config: LicenseClientConfig):
        self.config = config

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except Exception:
            return None

    def _read_cache(self) -> dict[str, Any]:
        if not self.config.cache_file.exists():
            return {
                "license_key": "",
                "status": "unknown",
                "expires": "",
                "features": [],
                "last_validated_at": "",
                "grace_deadline": "",
                "signature": "",
            }
        try:
            raw = json.loads(self.config.cache_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
        return {
            "license_key": "",
            "status": "unknown",
            "expires": "",
            "features": [],
            "last_validated_at": "",
            "grace_deadline": "",
            "signature": "",
        }

    def _write_cache(self, payload: dict[str, Any]) -> None:
        self.config.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def set_license_key(self, license_key: str) -> dict[str, Any]:
        cache = self._read_cache()
        cache["license_key"] = (license_key or "").strip()
        cache.setdefault("status", "unknown")
        cache.setdefault("expires", "")
        cache.setdefault("features", [])
        cache.setdefault("last_validated_at", "")
        cache.setdefault("grace_deadline", "")
        cache.setdefault("signature", "")
        self._write_cache(cache)
        return cache

    def _online_validate(self, license_key: str, server_ip: str | None, fingerprint_hash: str | None) -> dict[str, Any]:
        endpoint = self.config.base_url.rstrip("/") + self.config.validate_path
        body = {
            "license_key": license_key,
            "server_ip": server_ip,
            "fingerprint_hash": fingerprint_hash,
        }
        data = json.dumps(body).encode("utf-8")
        request = Request(
            endpoint,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError("Invalid license API response format")
            return payload

    def validate(self, license_key: str | None = None, server_ip: str | None = None, fingerprint_hash: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
        cache = self._read_cache()
        key = (license_key or cache.get("license_key", "")).strip()
        if not key:
            return {
                "valid": False,
                "status": "missing",
                "source": "cache",
                "message": "No license key in cache. Set a license key before validation.",
                "hint": ISO_FMT_HINT,
            }

        now = self._now()
        expires_dt = self._parse_dt(str(cache.get("expires", "")))
        grace_dt = self._parse_dt(str(cache.get("grace_deadline", "")))
        cache_active = str(cache.get("status", "")).lower() == "active"
        not_expired = bool(expires_dt and expires_dt > now)

        if not force_refresh and cache_active and not_expired and str(cache.get("license_key", "")).strip() == key:
            return {
                "valid": True,
                "status": "active",
                "source": "cache",
                "license_key": key,
                "expires": cache.get("expires", ""),
                "features": cache.get("features", []),
                "grace_deadline": cache.get("grace_deadline", ""),
                "message": "License validated from local cache.",
            }

        try:
            online = self._online_validate(license_key=key, server_ip=server_ip, fingerprint_hash=fingerprint_hash)
            valid = bool(online.get("valid", False))
            status = str(online.get("status", "active" if valid else "inactive"))
            updated = {
                "license_key": key,
                "status": status,
                "expires": str(online.get("expires", cache.get("expires", ""))),
                "features": list(online.get("features", cache.get("features", [])) or []),
                "last_validated_at": now.isoformat(),
                "grace_deadline": (now + timedelta(hours=self.config.grace_hours)).isoformat(),
                "signature": str(online.get("signature", cache.get("signature", ""))),
            }
            self._write_cache(updated)
            return {
                "valid": valid,
                "status": status,
                "source": "license-api",
                "license_key": key,
                "expires": updated["expires"],
                "features": updated["features"],
                "grace_deadline": updated["grace_deadline"],
                "message": "License validated against central license API.",
            }
        except (URLError, HTTPError, TimeoutError, RuntimeError, ValueError):
            if cache_active and grace_dt and grace_dt > now and str(cache.get("license_key", "")).strip() == key:
                return {
                    "valid": True,
                    "status": "grace",
                    "source": "cache-grace",
                    "license_key": key,
                    "expires": cache.get("expires", ""),
                    "features": cache.get("features", []),
                    "grace_deadline": cache.get("grace_deadline", ""),
                    "message": "Central license API unavailable; grace period is active.",
                }
            return {
                "valid": False,
                "status": "unreachable",
                "source": "license-api",
                "license_key": key,
                "expires": cache.get("expires", ""),
                "features": cache.get("features", []),
                "grace_deadline": cache.get("grace_deadline", ""),
                "message": "Central license API unavailable and no active grace window.",
            }
