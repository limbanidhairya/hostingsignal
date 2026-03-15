"""Background local metrics collector for the developer panel."""
from __future__ import annotations

import asyncio
import logging
import os
import time

import psutil
from sqlalchemy import select

from api.config import get_settings
from api.database import ManagedServer, async_session
from services.cluster_manager import cluster_manager

logger = logging.getLogger(__name__)
settings = get_settings()


class LocalMonitorService:
    async def run(self):
        while True:
            try:
                await self.collect_once()
            except Exception as exc:  # noqa: BLE001
                logger.warning("local monitor collection failed: %s", exc)
            await asyncio.sleep(max(5, settings.MONITOR_INTERVAL))

    async def collect_once(self):
        hostname = (settings.LOCAL_SERVER_HOSTNAME or "backend").strip()
        async with async_session() as session:
            result = await session.execute(
                select(ManagedServer).where(ManagedServer.hostname == hostname).limit(1)
            )
            server = result.scalar_one_or_none()
            if server is None:
                return

            metrics = self._collect_metrics()
            await cluster_manager.heartbeat(session, str(server.id), metrics=metrics)

    def _collect_metrics(self) -> dict:
        disk = psutil.disk_usage("/")
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()
        boot_time = psutil.boot_time()
        load_avg = None
        if hasattr(os, "getloadavg"):
            try:
                load_avg = os.getloadavg()[0]
            except OSError:
                load_avg = None

        return {
            "panel_version": settings.APP_VERSION,
            "cpu_cores": psutil.cpu_count() or 1,
            "ram_mb": int(vm.total / (1024 * 1024)),
            "disk_gb": int(disk.total / (1024 * 1024 * 1024)),
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "ram_percent": vm.percent,
            "disk_percent": disk.percent,
            "network_in_mbps": round((net.bytes_recv * 8) / 1_000_000, 3),
            "network_out_mbps": round((net.bytes_sent * 8) / 1_000_000, 3),
            "load_average": load_avg,
            "active_connections": len(psutil.net_connections()),
            "uptime_seconds": int(max(0, time.time() - boot_time)),
        }


local_monitor_service = LocalMonitorService()