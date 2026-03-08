"""Developer Panel — Analytics API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import random

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/dashboard")
async def analytics_dashboard(period: str = "7d"):
    """Get analytics dashboard data."""
    days = int(period.replace("d", "")) if period.endswith("d") else 7
    return {
        "period": period,
        "total_installations": random.randint(800, 1500),
        "active_licenses": random.randint(500, 1000),
        "new_installs_today": random.randint(5, 25),
        "revenue_mtd": round(random.uniform(5000, 15000), 2),
        "top_tiers": {
            "starter": random.randint(200, 500),
            "professional": random.randint(200, 400),
            "business": random.randint(50, 150),
            "enterprise": random.randint(10, 50),
        },
        "daily_installs": [{"date": (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"), "count": random.randint(5, 30)} for i in range(days)],
    }


@router.get("/installations")
async def installation_analytics(region: Optional[str] = None):
    """Get installation analytics by region/OS."""
    return {
        "by_os": {"ubuntu_22": 45, "ubuntu_24": 30, "debian_12": 15, "almalinux_9": 10},
        "by_webserver": {"openlitespeed": 72, "apache": 28},
        "by_region": {"US": 35, "EU": 28, "Asia": 22, "Other": 15},
        "by_php": {"8.2": 40, "8.1": 30, "8.3": 20, "8.0": 8, "7.4": 2},
    }


@router.get("/plugins/stats")
async def plugin_analytics():
    """Get plugin download/usage analytics."""
    return {
        "total_downloads": random.randint(5000, 20000),
        "top_plugins": [
            {"name": "HS Security Suite", "downloads": random.randint(1000, 5000)},
            {"name": "HS Backup Pro", "downloads": random.randint(800, 3000)},
            {"name": "HS Email Manager", "downloads": random.randint(500, 2000)},
            {"name": "HS Analytics", "downloads": random.randint(400, 1500)},
            {"name": "HS Cache Optimizer", "downloads": random.randint(300, 1000)},
        ],
    }


@router.get("/revenue")
async def revenue_analytics(period: str = "30d"):
    """Revenue analytics."""
    days = int(period.replace("d", "")) if period.endswith("d") else 30
    return {
        "period": period,
        "total_revenue": round(random.uniform(10000, 50000), 2),
        "license_revenue": round(random.uniform(8000, 40000), 2),
        "plugin_revenue": round(random.uniform(2000, 10000), 2),
        "daily_revenue": [{"date": (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"), "amount": round(random.uniform(200, 800), 2)} for i in range(days)],
    }
