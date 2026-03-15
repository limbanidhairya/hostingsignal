"""
HostingSignal Developer Panel — Main Application
=================================================
Central control panel for panel developers/operators.
Install location: /opt/hostingsignal-developer
"""
from contextlib import asynccontextmanager
import asyncio
import importlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.database import init_db
from api.config import get_settings
from services.local_monitor import local_monitor_service


def _load_router(module_name: str):
    """Load optional routers without crashing startup when dependencies are missing."""
    try:
        module = importlib.import_module(module_name)
        return getattr(module, "router", None)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Optional router '{module_name}' unavailable: {exc}")
        return None

VERSION = "1.0.0"
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 HostingSignal Developer Panel v{VERSION}")
    monitor_task = None
    try:
        await init_db()
        print("✅ Database tables initialized")
        if settings.LOCAL_MONITOR_ENABLED:
            monitor_task = asyncio.create_task(local_monitor_service.run())
    except Exception as e:
        print(f"⚠️ Database connection failed, running in mock mode: {e}")
    yield
    if monitor_task is not None:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    print("👋 Shutting down Developer Panel")


app = FastAPI(
    title="HostingSignal Developer Panel",
    description="Central management for licenses, plugins, clusters, updates & analytics",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(auth_router)

optional_router_modules = [
    "api.internal_services",
    "api.system",
    "api.shell",
    "api.licenses",
    "api.plugins",
    "api.updates",
    "api.clusters",
    "api.analytics",
    "api.monitoring",
    "api.software",
    "api.containers",
    "api.whmcs",
]

for module_name in optional_router_modules:
    router = _load_router(module_name)
    if router is not None:
        app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "developer-panel", "version": VERSION}


if __name__ == "__main__":
    import uvicorn
    # Enforcing Port 2087 for definitive HS-Panel API standard
    uvicorn.run(app, host="0.0.0.0", port=2087)

