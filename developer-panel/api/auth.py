"""Developer Panel — Auth API (DB + JWT)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import Admin, DevAdmin, get_db

router = APIRouter(prefix="/api/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
settings = get_settings()


class LoginRequest(BaseModel):
    identifier: str | None = None
    email: str | None = None
    username: str | None = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


def _create_access_token(subject: str, role: str, expires_hours: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {
        "sub": subject,
        "role": role,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def _get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> DevAdmin:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token subject")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    result = await db.execute(select(DevAdmin).where(DevAdmin.email == email, DevAdmin.is_active == True))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin account not found")
    return admin


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> DevAdmin:
    return await _get_current_admin(credentials, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate installer-seeded panel admin or existing dev admin user."""
    identifier = (body.identifier or body.username or body.email or "").strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Username or email is required")

    panel_admin_result = await db.execute(select(Admin).where(Admin.username == identifier).limit(1))
    panel_admin = panel_admin_result.scalar_one_or_none()

    admin: DevAdmin | None = None
    if panel_admin and pwd_context.verify(body.password, panel_admin.password_hash):
        dev_admin_result = await db.execute(
            select(DevAdmin).where(DevAdmin.username == panel_admin.username, DevAdmin.is_active == True).limit(1)
        )
        admin = dev_admin_result.scalar_one_or_none()
        if admin is None:
            admin = DevAdmin(
                username=panel_admin.username,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=panel_admin.password_hash,
                role="admin",
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
    else:
        result = await db.execute(
            select(DevAdmin).where(
                DevAdmin.is_active == True,
                (DevAdmin.email == identifier) | (DevAdmin.username == identifier),
            )
        )
        admin = result.scalar_one_or_none()
        if not admin or not pwd_context.verify(body.password, admin.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

    admin.last_login = datetime.utcnow()
    await db.commit()

    token = _create_access_token(
        subject=admin.email,
        role=admin.role,
        expires_hours=settings.JWT_EXPIRY_HOURS,
    )
    return TokenResponse(access_token=token, expires_in=settings.JWT_EXPIRY_HOURS * 3600)


@router.post("/logout")
async def logout():
    # Stateless JWT flow: client discards token.
    return {"status": "logged_out"}


@router.get("/me")
async def me(admin: DevAdmin = Depends(_get_current_admin)):
    return {
        "id": str(admin.id),
        "email": admin.email,
        "username": admin.username,
        "role": admin.role,
        "is_active": admin.is_active,
    }
