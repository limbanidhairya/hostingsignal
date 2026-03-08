"""
AI Monitoring Microservice — Metrics Collector
Collects system metrics: CPU, RAM, Disk, Network, Services
Install location: /usr/local/hostingsignal/monitoring
"""
import os
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

METRICS_DIR = "/usr/local/hostingsignal/monitoring/data"
HISTORY_SIZE = 1440  # 24 hours at 1-minute intervals


class MetricsCollector:
    """Collects system metrics using psutil and stores historical data."""

    def __init__(self):
        self.history: List[dict] = []
        self.running = False
        self.interval = 60  # seconds
        os.makedirs(METRICS_DIR, exist_ok=True)

    def collect_cpu(self) -> dict:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            per_cpu = psutil.cpu_percent(interval=0, percpu=True)
            load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

            return {
                "percent": cpu_percent,
                "frequency_mhz": cpu_freq.current if cpu_freq else 0,
                "cores": cpu_count,
                "per_core": per_cpu,
                "load_avg_1m": load_avg[0],
                "load_avg_5m": load_avg[1],
                "load_avg_15m": load_avg[2],
            }
        except ImportError:
            return self._fallback_cpu()

    def _fallback_cpu(self) -> dict:
        """Fallback CPU collection using /proc/stat."""
        try:
            with open("/proc/stat") as f:
                line = f.readline()
            parts = line.split()
            idle = int(parts[4])
            total = sum(int(x) for x in parts[1:])
            load_avg = [float(x) for x in open("/proc/loadavg").read().split()[:3]]
            return {
                "percent": round(100 - (idle / total * 100), 1),
                "cores": os.cpu_count() or 1,
                "load_avg_1m": load_avg[0],
                "load_avg_5m": load_avg[1],
                "load_avg_15m": load_avg[2],
            }
        except Exception:
            return {"percent": 0, "cores": 1}

    def collect_memory(self) -> dict:
        try:
            import psutil
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total_mb": round(mem.total / 1048576),
                "used_mb": round(mem.used / 1048576),
                "available_mb": round(mem.available / 1048576),
                "percent": mem.percent,
                "swap_total_mb": round(swap.total / 1048576),
                "swap_used_mb": round(swap.used / 1048576),
                "swap_percent": swap.percent,
            }
        except ImportError:
            return self._fallback_memory()

    def _fallback_memory(self) -> dict:
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            info = {}
            for line in lines:
                parts = line.split()
                info[parts[0].rstrip(":")] = int(parts[1])
            total = info.get("MemTotal", 0)
            free = info.get("MemAvailable", info.get("MemFree", 0))
            used = total - free
            return {
                "total_mb": round(total / 1024),
                "used_mb": round(used / 1024),
                "available_mb": round(free / 1024),
                "percent": round(used / total * 100, 1) if total > 0 else 0,
            }
        except Exception:
            return {"percent": 0}

    def collect_disk(self) -> dict:
        try:
            import psutil
            partitions = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    partitions.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / 1073741824, 2),
                        "used_gb": round(usage.used / 1073741824, 2),
                        "free_gb": round(usage.free / 1073741824, 2),
                        "percent": usage.percent,
                    })
                except PermissionError:
                    continue

            io = psutil.disk_io_counters()
            return {
                "partitions": partitions,
                "io_read_mb": round(io.read_bytes / 1048576, 1) if io else 0,
                "io_write_mb": round(io.write_bytes / 1048576, 1) if io else 0,
            }
        except ImportError:
            return self._fallback_disk()

    def _fallback_disk(self) -> dict:
        try:
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            used = total - free
            return {
                "partitions": [{
                    "device": "/",
                    "mountpoint": "/",
                    "total_gb": round(total / 1073741824, 2),
                    "used_gb": round(used / 1073741824, 2),
                    "free_gb": round(free / 1073741824, 2),
                    "percent": round(used / total * 100, 1) if total > 0 else 0,
                }]
            }
        except Exception:
            return {"partitions": []}

    def collect_network(self) -> dict:
        try:
            import psutil
            net = psutil.net_io_counters()
            connections = len(psutil.net_connections(kind="inet"))
            return {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "active_connections": connections,
            }
        except ImportError:
            return {"bytes_sent": 0, "bytes_recv": 0}

    def collect_services(self) -> List[dict]:
        """Check status of critical services."""
        services = [
            "hostingsignal-api", "hostingsignal-web",
            "hostingsignal-daemon", "hostingsignal-monitor",
            "nginx", "apache2", "httpd", "lsws",
            "mysql", "mariadb", "postgresql",
            "redis-server", "redis",
            "named", "postfix", "dovecot",
        ]
        results = []
        for svc in services:
            status = self._check_systemd_service(svc)
            if status is not None:
                results.append({"name": svc, "status": status})
        return results

    def _check_systemd_service(self, service: str) -> Optional[str]:
        try:
            import subprocess
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return None

    def collect_all(self) -> dict:
        """Collect all metrics in one call."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": self.collect_cpu(),
            "memory": self.collect_memory(),
            "disk": self.collect_disk(),
            "network": self.collect_network(),
            "services": self.collect_services(),
        }

    async def start_collection(self):
        """Start continuous metrics collection loop."""
        self.running = True
        logger.info("Metrics collection started")

        while self.running:
            try:
                metrics = self.collect_all()
                self.history.append(metrics)

                # Trim history
                if len(self.history) > HISTORY_SIZE:
                    self.history = self.history[-HISTORY_SIZE:]

                # Save hourly snapshots
                if datetime.utcnow().minute == 0:
                    self._save_snapshot(metrics)

            except Exception as e:
                logger.error(f"Metrics collection error: {e}")

            await asyncio.sleep(self.interval)

    def stop_collection(self):
        self.running = False
        logger.info("Metrics collection stopped")

    def _save_snapshot(self, metrics: dict):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        filepath = os.path.join(METRICS_DIR, f"metrics_{ts}.json")
        with open(filepath, "w") as f:
            json.dump(metrics, f)

    def get_latest(self) -> Optional[dict]:
        return self.history[-1] if self.history else self.collect_all()

    def get_history(self, minutes: int = 60) -> List[dict]:
        return self.history[-minutes:]


# Singleton
metrics_collector = MetricsCollector()
