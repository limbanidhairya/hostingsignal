"""
HostingSignal License Server — Crypto Utilities
Encryption, hashing, and key generation.
"""
import hashlib
import secrets
import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from config import settings


def generate_license_key() -> str:
    """Generate a license key in format HS-XXXX-XXXX-XXXX-XXXX."""
    prefix = settings.LICENSE_PREFIX
    segments = []
    for _ in range(4):
        seg = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(4))
        segments.append(seg)
    return f"{prefix}-{'-'.join(segments)}"


def hash_fingerprint(cpu_id: str, disk_uuid: str, mac_address: str, hostname: str, machine_id: str) -> str:
    """Create a SHA-256 hash of the server fingerprint components."""
    raw = f"{cpu_id}|{disk_uuid}|{mac_address}|{hostname}|{machine_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt via passlib."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def _get_fernet() -> Fernet:
    """Get a Fernet instance for symmetric encryption."""
    # Ensure key is 32 url-safe base64-encoded bytes
    key = settings.ENCRYPTION_KEY
    if len(key) != 44:  # Fernet key length
        key = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt_data(data: str) -> str:
    """Encrypt a string using Fernet symmetric encryption."""
    f = _get_fernet()
    return f.encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_data(encrypted: str) -> Optional[str]:
    """Decrypt an encrypted string. Returns None if decryption fails."""
    try:
        f = _get_fernet()
        return f.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return None


def generate_random_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)
