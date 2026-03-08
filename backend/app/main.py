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
from app.api.websites import router as websites_router
from app.api.monitoring import router as monitoring_router
from app.api.domains import router as domains_router
from app.api.dns import router as dns_router
from app.api.databases import router as databases_router
from app.api.email import router as email_router
from app.api.backups import router as backups_router
from app.api.security import router as security_router
from app.api.cluster import router as cluster_router
from app.api.php_manager import router as php_manager_router
from app.api.setup_wizard import router as setup_wizard_router
from app.monitoring.api import router as ai_monitoring_router


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
    import os
    import secrets

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            # Check env var for initial password, default to a random strong string if not provided
            initial_password = os.environ.get("ADMIN_PASSWORD", "".join(secrets.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(12)))
            
            admin_user = User(
                email="admin@hostingsignal.com",
                name="HostingSignal Admin",
                hashed_password=hash_password(initial_password),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"👤 Default admin user created (admin@hostingsignal.com / {initial_password})")
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

# CORS (Allow all domains/IPs for the control panel frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers — Original
app.include_router(auth_router)
app.include_router(licenses_router)
app.include_router(admin_router)
app.include_router(cyberpanel_router)
app.include_router(server_router)

# Mount routers — New modules
app.include_router(websites_router)
app.include_router(monitoring_router)
app.include_router(domains_router)
app.include_router(dns_router)
app.include_router(databases_router)
app.include_router(email_router)
app.include_router(backups_router)
app.include_router(security_router)
app.include_router(cluster_router)
app.include_router(php_manager_router)
app.include_router(setup_wizard_router)
app.include_router(ai_monitoring_router)


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
