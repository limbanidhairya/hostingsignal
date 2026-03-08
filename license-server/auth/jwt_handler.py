"""
HostingSignal License Server — JWT Token Handler
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError, ExpiredSignatureError

from config import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_license_token(license_key: str, fingerprint_hash: str, tier: str, expires_days: Optional[int] = None) -> str:
    """Create a signed license validation token returned to client panels."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=expires_days or settings.JWT_LICENSE_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": license_key,
        "fingerprint": fingerprint_hash,
        "tier": tier,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "license",
        "iss": "hostingsignal-license-server",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None


def verify_license_token(token: str) -> Optional[dict]:
    """Verify a license token and return its claims."""
    payload = decode_token(token)
    if payload and payload.get("type") == "license":
        return payload
    return None
