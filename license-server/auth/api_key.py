"""
HostingSignal License Server — API Key Validation
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import AdminUser


async def validate_master_api_key(api_key: str) -> bool:
    """Validate against the master API key from configuration."""
    return api_key == settings.MASTER_API_KEY


async def validate_user_api_key(api_key: str, db: AsyncSession) -> Optional[AdminUser]:
    """Validate a user's API key and return the associated user."""
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.api_key == api_key,
            AdminUser.is_active == True,
        )
    )
    return result.scalar_one_or_none()


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets
    return f"hs_key_{secrets.token_urlsafe(32)}"
