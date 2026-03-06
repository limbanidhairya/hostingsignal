from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.license import License, LicenseStatus
from app.schemas import DashboardStats, UserResponse
from app.core.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/dashboard", response_model=DashboardStats)
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get admin dashboard statistics."""
    # Users
    users_result = await db.execute(select(User))
    all_users = users_result.scalars().all()

    # Licenses
    licenses_result = await db.execute(select(License))
    all_licenses = licenses_result.scalars().all()

    tier_breakdown = {}
    from app.models.license import LicenseTier
    for tier in LicenseTier:
        tier_breakdown[tier.value] = len([l for l in all_licenses if l.tier == tier and l.status == LicenseStatus.ACTIVE])

    return DashboardStats(
        total_licenses=len(all_licenses),
        active_licenses=len([l for l in all_licenses if l.status == LicenseStatus.ACTIVE]),
        expired_licenses=len([l for l in all_licenses if l.status == LicenseStatus.EXPIRED]),
        suspended_licenses=len([l for l in all_licenses if l.status == LicenseStatus.SUSPENDED]),
        monthly_revenue=sum(l.monthly_revenue for l in all_licenses),
        tier_breakdown=tier_breakdown,
        total_users=len(all_users),
        active_users=len([u for u in all_users if u.is_active]),
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = select(User)
    if role:
        query = query.where(User.role == UserRole(role))
    if search:
        query = query.where(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    email: str,
    name: str,
    password: str,
    role: str = "client",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        role=UserRole(role),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if name is not None:
        user.name = name
    if role is not None:
        user.role = UserRole(role)
    if is_active is not None:
        user.is_active = is_active

    await db.flush()
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()
    return {"message": f"User {user.email} deleted"}
