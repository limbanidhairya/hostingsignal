"""HS-Panel backend API entrypoint (FastAPI)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth, domain, mysql, mail, dns, ssl, ftp, php, security, system, backup, cron

app = FastAPI(
    title="HS-Panel Backend API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "hspanel-backend-api"}


app.include_router(auth.router)
app.include_router(domain.router)
app.include_router(mysql.router)
app.include_router(mail.router)
app.include_router(dns.router)
app.include_router(ssl.router)
app.include_router(ftp.router)
app.include_router(php.router)
app.include_router(security.router)
app.include_router(system.router)
app.include_router(backup.router)
app.include_router(cron.router)
