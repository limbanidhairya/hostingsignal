"""Cluster Manager Service — Orchestrates multi-server clusters"""
import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import Cluster, ManagedServer, ServerMetric
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ClusterManagerService:
    """Manages server clusters, health monitoring, and node orchestration."""

    async def create_cluster(self, db: AsyncSession, name: str, description: str = "",
                             region: str = "", max_servers: int = 50, config: dict = None) -> Cluster:
        cluster = Cluster(
            name=name, description=description, region=region,
            max_servers=max_servers, config=config or {},
        )
        db.add(cluster)
        await db.commit()
        await db.refresh(cluster)
        logger.info(f"Cluster created: {name}")
        return cluster

    async def delete_cluster(self, db: AsyncSession, cluster_id: str):
        result = await db.execute(select(Cluster).where(Cluster.id == cluster_id))
        cluster = result.scalar_one_or_none()
        if not cluster:
            raise ValueError("Cluster not found")
        # Unassign all servers first
        await db.execute(
            update(ManagedServer).where(ManagedServer.cluster_id == cluster_id).values(cluster_id=None)
        )
        await db.delete(cluster)
        await db.commit()
        logger.info(f"Cluster deleted: {cluster.name}")

    async def register_server(self, db: AsyncSession, hostname: str, ip_address: str,
                              port: int = 8000, cluster_id: str = None,
                              os_info: str = None, license_key: str = None) -> ManagedServer:
        server = ManagedServer(
            hostname=hostname, ip_address=ip_address, port=port,
            cluster_id=cluster_id, os_info=os_info, license_key=license_key,
            status="unknown", last_heartbeat=datetime.utcnow(),
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)
        logger.info(f"Server registered: {hostname} ({ip_address})")
        return server

    async def remove_server(self, db: AsyncSession, server_id: str):
        result = await db.execute(select(ManagedServer).where(ManagedServer.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            raise ValueError("Server not found")
        await db.delete(server)
        await db.commit()
        logger.info(f"Server removed: {server.hostname}")

    async def join_cluster(self, db: AsyncSession, server_id: str, cluster_id: str) -> ManagedServer:
        result = await db.execute(select(ManagedServer).where(ManagedServer.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            raise ValueError("Server not found")

        cluster_result = await db.execute(select(Cluster).where(Cluster.id == cluster_id))
        cluster = cluster_result.scalar_one_or_none()
        if not cluster:
            raise ValueError("Cluster not found")

        # Check capacity
        count = (await db.execute(
            select(func.count(ManagedServer.id)).where(ManagedServer.cluster_id == cluster_id)
        )).scalar()
        if count >= cluster.max_servers:
            raise ValueError(f"Cluster {cluster.name} is at capacity ({cluster.max_servers})")

        server.cluster_id = cluster_id
        await db.commit()
        await db.refresh(server)
        logger.info(f"Server {server.hostname} joined cluster {cluster.name}")
        return server

    async def leave_cluster(self, db: AsyncSession, server_id: str) -> ManagedServer:
        result = await db.execute(select(ManagedServer).where(ManagedServer.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            raise ValueError("Server not found")
        server.cluster_id = None
        await db.commit()
        await db.refresh(server)
        return server

    async def heartbeat(self, db: AsyncSession, server_id: str, metrics: dict = None) -> dict:
        result = await db.execute(select(ManagedServer).where(ManagedServer.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            raise ValueError("Server not found")

        server.status = "online"
        server.last_heartbeat = datetime.utcnow()
        if metrics:
            server.panel_version = metrics.get("panel_version", server.panel_version)
            server.cpu_cores = metrics.get("cpu_cores", server.cpu_cores)
            server.ram_mb = metrics.get("ram_mb", server.ram_mb)
            server.disk_gb = metrics.get("disk_gb", server.disk_gb)

            metric = ServerMetric(
                server_id=server_id,
                cpu_percent=metrics.get("cpu_percent"),
                ram_percent=metrics.get("ram_percent"),
                disk_percent=metrics.get("disk_percent"),
                network_in_mbps=metrics.get("network_in_mbps"),
                network_out_mbps=metrics.get("network_out_mbps"),
                load_average=metrics.get("load_average"),
                active_connections=metrics.get("active_connections"),
                uptime_seconds=metrics.get("uptime_seconds"),
            )
            db.add(metric)

        await db.commit()
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    async def check_stale_servers(self, db: AsyncSession):
        """Mark servers as offline if no heartbeat within threshold."""
        threshold = datetime.utcnow() - timedelta(seconds=settings.CLUSTER_TIMEOUT)
        await db.execute(
            update(ManagedServer)
            .where(ManagedServer.last_heartbeat < threshold, ManagedServer.status == "online")
            .values(status="offline")
        )
        await db.commit()

    async def get_cluster_health(self, db: AsyncSession, cluster_id: str) -> dict:
        result = await db.execute(
            select(ManagedServer).where(ManagedServer.cluster_id == cluster_id)
        )
        servers = result.scalars().all()
        total = len(servers)
        online = sum(1 for s in servers if s.status == "online")
        offline = sum(1 for s in servers if s.status == "offline")

        return {
            "cluster_id": str(cluster_id),
            "total_servers": total,
            "online": online,
            "offline": offline,
            "health_percent": round(online / total * 100, 1) if total > 0 else 0,
        }

    async def push_command(self, server: ManagedServer, command: str, payload: dict = None) -> dict:
        """Send a command to a managed server via its API."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"http://{server.ip_address}:{server.port}/api/internal/command",
                    json={"command": command, "payload": payload or {}},
                    headers={"X-Cluster-Key": settings.LICENSE_API_KEY},
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to push command to {server.hostname}: {e}")
            return {"error": str(e)}


cluster_manager = ClusterManagerService()
