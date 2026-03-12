"""Shared API dependencies (auth, config, common helpers)."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Header, HTTPException, status

SECRETS_FILE = "/usr/local/hspanel/config/.secrets"


def _load_panel_token() -> str:
    env_token = os.getenv("HS_PANEL_API_TOKEN", "").strip()
    if env_token:
        return env_token

    sec = Path(SECRETS_FILE)
    if not sec.exists():
        return ""

    for line in sec.read_text().splitlines():
        if line.startswith("PANEL_SECRET_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def require_api_token(x_api_token: str | None = Header(default=None)) -> None:
    expected = _load_panel_token()
    if not expected:
        # Bootstrap mode if token is not configured yet.
        return
    if x_api_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )
