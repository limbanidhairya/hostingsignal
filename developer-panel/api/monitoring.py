"""Developer Panel — Server Monitoring API"""
from fastapi import APIRouter
from typing import Optional
from datetime import datetime, timezone
import random

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


@router.get("/servers")
async def list_monitored_servers():
    """Get all monitored panel servers."""
    return {
        "servers": [
            {"hostname": "panel-us-1.hostingsignal.com", "ip": "203.0.113.10", "status": "healthy", "cpu": random.randint(10, 40), "ram": random.randint(30, 60), "disk": random.randint(20, 50), "uptime": "42d 5h"},
            {"hostname": "panel-eu-1.hostingsignal.com", "ip": "198.51.100.20", "status": "healthy", "cpu": random.randint(10, 40), "ram": random.randint(30, 60), "disk": random.randint(20, 50), "uptime": "18d 12h"},
            {"hostname": "panel-ap-1.hostingsignal.com", "ip": "192.0.2.30", "status": "warning", "cpu": random.randint(60, 85), "ram": random.randint(70, 90), "disk": random.randint(40, 60), "uptime": "7d 3h"},
        ]
    }


@router.get("/alerts")
async def active_alerts():
    """Get active alerts from monitored servers."""
    return {
        "alerts": [
            {"severity": "warning", "server": "panel-ap-1", "message": "High CPU usage (78%)", "time": datetime.now(timezone.utc).isoformat()},
            {"severity": "info", "server": "panel-us-1", "message": "SSL certificate expiring in 14 days", "time": datetime.now(timezone.utc).isoformat()},
        ]
    }


@router.get("/services/{hostname}")
async def server_services(hostname: str):
    """Get service statuses for a specific server."""
    return {
        "hostname": hostname,
        "services": {
            "hostingsignal-api": "active",
            "hostingsignal-web": "active",
            "hostingsignal-daemon": "active",
            "hostingsignal-monitor": "active",
            "lsws": "active",
            "postgresql": "active",
            "redis": "active",
        },
    }
