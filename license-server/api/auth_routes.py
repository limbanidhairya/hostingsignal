"""
HostingSignal License Server — Auth API Routes
Login, token refresh, API key management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import AdminUser
from auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from auth.api_key import generate_api_key
from middleware.auth_middleware import get_current_user, require_superadmin
from middleware.rate_limiter import limiter
from utils.crypto import verify_password, hash_password
from utils.validators import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and receive JWT tokens."""
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.email == body.email.lower(),
            AdminUser.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_superadmin": user.is_superadmin,
        }
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request):
    """Get a new access token using a refresh token."""
    body = await request.json()
    token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token = create_access_token(data={"sub": payload["sub"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


@router.post("/api-key/generate")
async def generate_api_key_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate a new API key for the current user."""
    if current_user.get("type") == "api_key":
        raise HTTPException(status_code=400, detail="Cannot generate API key while authenticated via API key")

    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")

    from uuid import UUID
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_key = generate_api_key()
    user.api_key = new_key
    await db.flush()

    return {"api_key": new_key, "message": "API key generated. Store it securely — it won't be shown again."}


@router.post("/users/create")
async def create_admin_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_superadmin),
):
    """Create a new admin user. Requires superadmin."""
    body = await request.json()
    email = body.get("email", "").lower()
    name = body.get("name", "")
    password = body.get("password", "")
    is_superadmin = body.get("is_superadmin", False)

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    existing = await db.execute(select(AdminUser).where(AdminUser.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = AdminUser(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        is_superadmin=is_superadmin,
    )
    db.add(user)
    await db.flush()

    return {"message": f"User {email} created successfully", "user_id": str(user.id)}
