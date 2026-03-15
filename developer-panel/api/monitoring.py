"""Developer Panel — Server Monitoring API (DB-backed)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, ManagedServer, ServerMetric, Cluster

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


@router.get("/servers")
async def list_monitored_servers(db: AsyncSession = Depends(get_db)):
    """Get all monitored panel servers."""
    result = await db.execute(select(ManagedServer).order_by(ManagedServer.created_at.desc()))
    servers = result.scalars().all()

    # Pre-fetch clusters for region lookup
    cluster_ids = {s.cluster_id for s in servers if s.cluster_id}
    clusters = {}
    if cluster_ids:
        cr = await db.execute(select(Cluster).where(Cluster.id.in_(cluster_ids)))
        for c in cr.scalars().all():
            clusters[c.id] = c

    output = []
    for server in servers:
        metric_result = await db.execute(
            select(ServerMetric)
            .where(ServerMetric.server_id == server.id)
            .order_by(ServerMetric.recorded_at.desc())
            .limit(1)
        )
        metric = metric_result.scalar_one_or_none()
        cluster = clusters.get(server.cluster_id)
        metadata = server.metadata_ or {}
        region = cluster.region if cluster else metadata.get("region") or metadata.get("location")
        output.append(
            {
                "id": str(server.id),
                "hostname": server.hostname,
                "ip": server.ip_address,
                "status": server.status,
                "cpu": metric.cpu_percent if metric else None,
                "ram": metric.ram_percent if metric else None,
                "disk": metric.disk_percent if metric else None,
                "uptime_seconds": metric.uptime_seconds if metric else None,
                "last_heartbeat": server.last_heartbeat.isoformat() if server.last_heartbeat else None,
                "region": region,
                "cluster_name": cluster.name if cluster else None,
            }
        )

    return {"servers": output}


@router.get("/alerts")
async def active_alerts(db: AsyncSession = Depends(get_db)):
    """Get active alerts from latest metric snapshots."""
    result = await db.execute(select(ManagedServer))
    servers = result.scalars().all()
    alerts = []

    for server in servers:
        metric_result = await db.execute(
            select(ServerMetric)
            .where(ServerMetric.server_id == server.id)
            .order_by(ServerMetric.recorded_at.desc())
            .limit(1)
        )
        metric = metric_result.scalar_one_or_none()
        if not metric:
            continue

        if metric.cpu_percent is not None and metric.cpu_percent >= 85:
            alerts.append(
                {
                    "severity": "warning",
                    "server": server.hostname,
                    "message": f"High CPU usage ({metric.cpu_percent:.1f}%)",
                    "time": datetime.now(timezone.utc).isoformat(),
                }
            )

        if metric.ram_percent is not None and metric.ram_percent >= 90:
            alerts.append(
                {
                    "severity": "warning",
                    "server": server.hostname,
                    "message": f"High RAM usage ({metric.ram_percent:.1f}%)",
                    "time": datetime.now(timezone.utc).isoformat(),
                }
            )

    return {"alerts": alerts}


@router.get("/services/{hostname}")
async def server_services(hostname: str, db: AsyncSession = Depends(get_db)):
    """Get service statuses for a specific server.

    Remote per-service telemetry is not yet stored; this endpoint reports
    server heartbeat state and returns placeholders for service status.
    """
    result = await db.execute(select(ManagedServer).where(ManagedServer.hostname == hostname))
    server = result.scalar_one_or_none()
    if not server:
        return {"hostname": hostname, "services": {}, "message": "Server not found"}

    state = "active" if server.status == "online" else "degraded"
    return {
        "hostname": hostname,
        "services": {
            "lsws": state,
            "mariadb": state,
            "postfix": state,
            "dovecot": state,
            "pdns": state,
            "pure-ftpd": state,
            "docker": state,
            "csf": state,
            "hostingsignal-api": state,
            "hostingsignal-web": state,
            "hostingsignal-daemon": state,
        },
        "source": "cluster-heartbeat-derived",
    }
