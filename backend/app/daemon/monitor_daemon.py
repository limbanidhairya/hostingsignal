"""
HostingSignal Panel — Monitor Daemon
Background service for continuous system monitoring.
Collects metrics and stores in Redis for real-time WebSocket delivery.
"""
import asyncio
import json
import time
from datetime import datetime, timezone


class MonitorDaemon:
    """Background system monitor that collects and caches metrics."""

    def __init__(self, redis_client=None, interval: int = 5):
        self.redis_client = redis_client
        self.interval = interval
        self._running = False
        self._metrics_history = []

    async def start(self):
        """Start the monitoring loop."""
        self._running = True
        print("🔍 Monitor daemon started")
        while self._running:
            try:
                metrics = self._collect_metrics()
                await self._store_metrics(metrics)
                await asyncio.sleep(self.interval)
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(self.interval)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        print("🔍 Monitor daemon stopped")

    def _collect_metrics(self) -> dict:
        """Collect current system metrics."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "net_bytes_sent": net.bytes_sent,
                "net_bytes_recv": net.bytes_recv,
                "load_avg_1": load_avg[0],
                "load_avg_5": load_avg[1],
                "load_avg_15": load_avg[2],
            }
        except ImportError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_percent": 0,
                "memory_percent": 0,
                "error": "psutil not installed",
            }

    async def _store_metrics(self, metrics: dict):
        """Store metrics in Redis for real-time access."""
        if self.redis_client:
            await self.redis_client.set("hs:metrics:latest", metrics, expire=30)

            # Store in time-series (keep last 1000 points)
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > 1000:
                self._metrics_history = self._metrics_history[-1000:]

            await self.redis_client.set(
                "hs:metrics:history",
                self._metrics_history[-100:],  # Store last 100 in Redis
                expire=3600,
            )


# Singleton instance
monitor_daemon = MonitorDaemon()
