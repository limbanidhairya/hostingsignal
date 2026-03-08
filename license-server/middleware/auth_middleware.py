"""
HostingSignal License Server — Auth Middleware
JWT and API Key authentication for protected routes.
"""
from typing import Optional

from fastapi import Request, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import decode_token
from auth.api_key import validate_master_api_key, validate_user_api_key
from database.connection import get_db

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Authenticate via JWT Bearer token or X-API-Key header.
    Returns user info dict on success, raises 401 on failure.
    """
    # Try API key first
    if x_api_key:
        # Check master API key
        if await validate_master_api_key(x_api_key):
            return {
                "type": "api_key",
                "email": "system@hostingsignal.com",
                "is_superadmin": True,
            }
        # Check user API key
        user = await validate_user_api_key(x_api_key, db)
        if user:
            return {
                "type": "api_key",
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "is_superadmin": user.is_superadmin,
            }

    # Try JWT token
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            return {
                "type": "jwt",
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "is_superadmin": payload.get("is_superadmin", False),
            }

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a valid JWT token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require superadmin privileges."""
    if not current_user.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Superadmin access required.")
    return current_user
