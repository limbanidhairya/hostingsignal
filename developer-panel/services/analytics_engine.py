"""Analytics Engine Service — Aggregates panel analytics data"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import AnalyticsEvent, ManagedServer, ServerMetric
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalyticsEngineService:
    """Aggregates, queries, and reports on panel analytics data."""

    async def record_event(self, db: AsyncSession, event_type: str, server_id: str = None,
                           license_key: str = None, panel_version: str = None,
                           os_info: str = None, metadata: dict = None, ip_address: str = None):
        event = AnalyticsEvent(
            event_type=event_type, server_id=server_id, license_key=license_key,
            panel_version=panel_version, os_info=os_info,
            metadata_=metadata or {}, ip_address=ip_address,
        )
        db.add(event)
        await db.commit()

    async def get_install_stats(self, db: AsyncSession, days: int = 30) -> dict:
        since = datetime.utcnow() - timedelta(days=days)
        total = (await db.execute(
            select(func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.event_type == "install", AnalyticsEvent.recorded_at >= since)
        )).scalar() or 0

        # Group by day
        daily = await db.execute(
            select(
                func.date(AnalyticsEvent.recorded_at).label("day"),
                func.count(AnalyticsEvent.id).label("count")
            )
            .where(AnalyticsEvent.event_type == "install", AnalyticsEvent.recorded_at >= since)
            .group_by(func.date(AnalyticsEvent.recorded_at))
            .order_by(func.date(AnalyticsEvent.recorded_at))
        )

        return {
            "total_installs": total,
            "period_days": days,
            "daily": [{"date": str(row.day), "count": row.count} for row in daily],
        }

    async def get_version_distribution(self, db: AsyncSession) -> list:
        result = await db.execute(
            select(
                ManagedServer.panel_version,
                func.count(ManagedServer.id).label("count")
            )
            .where(ManagedServer.panel_version.isnot(None))
            .group_by(ManagedServer.panel_version)
            .order_by(func.count(ManagedServer.id).desc())
        )
        return [{"version": row.panel_version, "count": row.count} for row in result]

    async def get_os_distribution(self, db: AsyncSession) -> list:
        result = await db.execute(
            select(
                ManagedServer.os_info,
                func.count(ManagedServer.id).label("count")
            )
            .where(ManagedServer.os_info.isnot(None))
            .group_by(ManagedServer.os_info)
            .order_by(func.count(ManagedServer.id).desc())
        )
        return [{"os": row.os_info, "count": row.count} for row in result]

    async def get_fleet_overview(self, db: AsyncSession) -> dict:
        total_servers = (await db.execute(select(func.count(ManagedServer.id)))).scalar() or 0
        online = (await db.execute(
            select(func.count(ManagedServer.id)).where(ManagedServer.status == "online")
        )).scalar() or 0
        offline = (await db.execute(
            select(func.count(ManagedServer.id)).where(ManagedServer.status == "offline")
        )).scalar() or 0

        # Average resource usage from latest metrics
        avg_cpu = (await db.execute(
            select(func.avg(ServerMetric.cpu_percent))
            .where(ServerMetric.recorded_at >= datetime.utcnow() - timedelta(minutes=5))
        )).scalar() or 0
        avg_ram = (await db.execute(
            select(func.avg(ServerMetric.ram_percent))
            .where(ServerMetric.recorded_at >= datetime.utcnow() - timedelta(minutes=5))
        )).scalar() or 0

        return {
            "total_servers": total_servers,
            "online": online,
            "offline": offline,
            "degraded": total_servers - online - offline,
            "avg_cpu_percent": round(avg_cpu, 1),
            "avg_ram_percent": round(avg_ram, 1),
        }

    async def get_event_timeline(self, db: AsyncSession, event_type: str = None,
                                 limit: int = 50) -> list:
        stmt = select(AnalyticsEvent).order_by(AnalyticsEvent.recorded_at.desc()).limit(limit)
        if event_type:
            stmt = stmt.where(AnalyticsEvent.event_type == event_type)
        result = await db.execute(stmt)
        events = result.scalars().all()
        return [{
            "id": str(e.id), "type": e.event_type,
            "panel_version": e.panel_version, "os_info": e.os_info,
            "ip_address": e.ip_address, "timestamp": e.recorded_at.isoformat(),
        } for e in events]

    async def get_error_rate(self, db: AsyncSession, hours: int = 24) -> dict:
        since = datetime.utcnow() - timedelta(hours=hours)
        total = (await db.execute(
            select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.recorded_at >= since)
        )).scalar() or 0
        errors = (await db.execute(
            select(func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.event_type == "error", AnalyticsEvent.recorded_at >= since)
        )).scalar() or 0

        return {
            "total_events": total,
            "errors": errors,
            "error_rate": round(errors / total * 100, 2) if total > 0 else 0,
            "period_hours": hours,
        }


analytics_engine = AnalyticsEngineService()
