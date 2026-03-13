"""
HostingSignal Developer Panel — Main Application
=================================================
Central control panel for panel developers/operators.
Install location: /opt/hostingsignal-developer
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.licenses import router as licenses_router
from api.plugins import router as plugins_router
from api.updates import router as updates_router
from api.clusters import router as clusters_router
from api.analytics import router as analytics_router
from api.monitoring import router as monitoring_router
from api.software import router as software_router
from api.auth import router as auth_router
from api.whmcs import router as whmcs_router
from api.database import init_db
from api.config import get_settings

VERSION = "1.0.0"
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 HostingSignal Developer Panel v{VERSION}")
    try:
        await init_db()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️ Database connection failed, running in mock mode: {e}")
    yield
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
app.include_router(licenses_router)
app.include_router(plugins_router)
app.include_router(updates_router)
app.include_router(clusters_router)
app.include_router(analytics_router)
app.include_router(monitoring_router)
app.include_router(software_router)
app.include_router(whmcs_router)


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "developer-panel", "version": VERSION}


if __name__ == "__main__":
    import uvicorn
    # Enforcing Port 2087 for definitive HS-Panel API standard
    uvicorn.run(app, host="0.0.0.0", port=2087)

