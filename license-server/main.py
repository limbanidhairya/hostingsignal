"""
HostingSignal License Server
=============================
Centralized license management and validation server.

Technology: FastAPI + PostgreSQL + Redis
Install location: /opt/hostingsignal-license
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from database.connection import init_db, async_session
from database.models import AdminUser
from api.license_routes import router as license_router
from api.auth_routes import router as auth_router
from middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from utils.crypto import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # ── Startup ──────────────────────────────────────────
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()

    # Seed default superadmin if none exists
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(AdminUser).where(AdminUser.is_superadmin == True)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            import secrets
            default_password = secrets.token_urlsafe(16)
            admin_user = AdminUser(
                email="admin@hostingsignal.com",
                name="System Admin",
                hashed_password=hash_password(default_password),
                is_active=True,
                is_superadmin=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"👤 Default superadmin created: admin@hostingsignal.com / {default_password}")
        else:
            print(f"👤 Superadmin exists: {admin.email}")

    print("✅ License Server ready")
    yield

    # ── Shutdown ─────────────────────────────────────────
    print(f"👋 Shutting down {settings.APP_NAME}")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Centralized license management and validation for HostingSignal Panel installations.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(license_router)
app.include_router(auth_router)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API info."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=4 if not settings.DEBUG else 1,
        log_level="info",
    )
