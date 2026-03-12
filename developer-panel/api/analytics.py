"""Developer Panel — Analytics API (service-backed)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, PluginSubmission
from ..services.analytics_engine import analytics_engine
from ..services.license_sync import license_sync

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get global dashboard stats."""
    fleet = await analytics_engine.get_fleet_overview(db)
    plugin_total = (await db.execute(select(func.count(PluginSubmission.id)))).scalar() or 0
    plugin_downloads = (await db.execute(select(func.sum(PluginSubmission.downloads)))).scalar() or 0

    total_licenses = 0
    active_licenses = 0
    try:
        lic_stats = await license_sync.get_license_stats()
        total_licenses = int(lic_stats.get("total", 0) or lic_stats.get("total_licenses", 0))
        active_licenses = int(lic_stats.get("active", 0) or lic_stats.get("active_licenses", 0))
    except Exception:
        # Keep analytics responsive even if license API is temporarily unavailable.
        pass

    timeline = await analytics_engine.get_event_timeline(db, limit=10)
    recent_activity = [
        {
            "text": f"{e['type']} event from {e.get('ip_address') or 'unknown-source'}",
            "time": e["timestamp"],
            "type": "info" if e["type"] != "error" else "warning",
        }
        for e in timeline
    ]

    return {
        "totalServers": fleet["total_servers"],
        "activeServers": fleet["online"],
        "totalLicenses": total_licenses,
        "activeLicenses": active_licenses,
        "totalPlugins": plugin_total,
        "totalDownloads": plugin_downloads,
        "recentActivity": recent_activity,
    }


@router.get("/installations")
async def installation_analytics(
    region: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get installation analytics from recorded events and server metadata."""
    install_stats = await analytics_engine.get_install_stats(db, days=days)
    by_os = await analytics_engine.get_os_distribution(db)
    by_version = await analytics_engine.get_version_distribution(db)

    return {
        "period_days": days,
        "region_filter": region,
        "installs": install_stats,
        "by_os": by_os,
        "by_version": by_version,
    }


@router.get("/plugins/stats")
async def plugin_analytics(db: AsyncSession = Depends(get_db)):
    """Get plugin download/usage analytics from DB."""
    total_downloads = (await db.execute(select(func.sum(PluginSubmission.downloads)))).scalar() or 0
    result = await db.execute(
        select(PluginSubmission)
        .order_by(PluginSubmission.downloads.desc())
        .limit(10)
    )
    plugins = result.scalars().all()
    return {
        "total_downloads": total_downloads,
        "top_plugins": [
            {
                "name": p.name,
                "slug": p.slug,
                "downloads": p.downloads,
                "rating": p.rating,
                "status": p.status,
            }
            for p in plugins
        ],
    }


@router.get("/revenue")
async def revenue_analytics(period: str = "30d"):
    """Revenue analytics placeholder until billing service is integrated."""
    # Billing backend is not integrated yet in this repo; return explicit placeholder.
    return {
        "period": period,
        "status": "not_configured",
        "message": "Revenue analytics will be available after billing service integration.",
    }
