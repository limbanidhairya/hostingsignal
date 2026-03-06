from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from app.core.license_verification import verify_panel_license, activate_license

from app.core.config import settings
from app.core.database import init_db
from app.api.auth import router as auth_router
from app.api.licenses import router as licenses_router
from app.api.admin import router as admin_router
from app.api.cyberpanel import router as cyberpanel_router
from app.api.server_api import router as server_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    print("✅ Database initialized")

    # Seed admin user if not exists
    from app.core.database import async_session
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            admin_user = User(
                email="admin@hostingsignal.com",
                name="Dhairya Limbani",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(admin_user)
            await session.commit()
            print("👤 Default admin user created (admin@hostingsignal.com / admin123)")
        else:
            print(f"👤 Admin user exists: {admin.email}")

    yield

    # Shutdown
    print(f"👋 Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="Web Hosting Control Panel with License Distribution",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# License Verification Middleware (Anti-Piracy Check)
@app.middleware("http")
async def license_check_middleware(request: Request, call_next):
    # Exempt auth and license checking endpoints themselves, and health checks
    exempt_paths = ["/api/health", "/api/system/activate-license", "/api/docs", "/api/openapi.json"]
    if any(request.url.path.startswith(p) for p in exempt_paths):
        return await call_next(request)

    # API endpoints require a valid license for this panel instance
    if request.url.path.startswith("/api/"):
        is_valid = await verify_panel_license()
        if not is_valid:
            return JSONResponse(
                status_code=402, 
                content={"detail": "License Required. This panel installation is not licensed."}
            )

    return await call_next(request)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router)
app.include_router(licenses_router)
app.include_router(admin_router)
app.include_router(cyberpanel_router)
app.include_router(server_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

@app.post("/api/system/activate-license")
async def handle_activate_license(request: Request):
    """Endpoint to apply a license key to this panel installation."""
    data = await request.json()
    key = data.get("key", "")
    if key.startswith("HS-"):
        success = activate_license(key)
        if success:
            return {"status": "success", "message": "License activated successfully."}
    return JSONResponse(status_code=400, content={"detail": "Invalid license key format or could not save."})


@app.get("/api/tiers")
async def get_tiers():
    """Public endpoint to get available license tiers and pricing."""
    from app.models.license import TIER_CONFIG
    return {
        tier.value: {
            "name": config["name"],
            "price_monthly": config["price_monthly"],
            "max_domains": config["max_domains"],
            "features": config["features"],
        }
        for tier, config in TIER_CONFIG.items()
    }
