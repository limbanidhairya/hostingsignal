"""Authentication and API token verification routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .deps import require_api_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/ping", dependencies=[Depends(require_api_token)])
def ping() -> dict:
    return {"success": True, "message": "authenticated"}
