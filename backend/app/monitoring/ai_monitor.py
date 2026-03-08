"""
HostingSignal Panel — AI Monitoring Microservice
==================================================
Install location: /usr/local/hostingsignal/monitoring
Features:
  - Predict high CPU usage
  - Predict disk failure
  - Detect unusual traffic
  - Detect service crashes
  - Metric collection: CPU, RAM, Disk, Network, Services
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
from collections import deque


class MetricsCollector:
    """Collects system metrics at regular intervals."""

    def __init__(self):
        self.history_cpu = deque(maxlen=360)      # 30 min at 5s intervals
        self.history_ram = deque(maxlen=360)
        self.history_disk = deque(maxlen=360)
        self.history_net_in = deque(maxlen=360)
        self.history_net_out = deque(maxlen=360)

    def collect(self) -> dict:
        """Collect current system metrics."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)

            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_percent": cpu,
                "ram_percent": mem.percent,
                "ram_used_gb": round(mem.used / (1024**3), 2),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "net_bytes_in": net.bytes_recv,
                "net_bytes_out": net.bytes_sent,
                "load_1": load[0],
                "load_5": load[1],
                "load_15": load[2],
            }
        except ImportError:
            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_percent": 0, "ram_percent": 0, "disk_percent": 0,
                "error": "psutil not installed",
            }

        self.history_cpu.append(metrics.get("cpu_percent", 0))
        self.history_ram.append(metrics.get("ram_percent", 0))
        self.history_disk.append(metrics.get("disk_percent", 0))
        self.history_net_in.append(metrics.get("net_bytes_in", 0))
        self.history_net_out.append(metrics.get("net_bytes_out", 0))

        return metrics

    def collect_services(self) -> dict:
        """Collect service statuses."""
        services = [
            "hostingsignal-api", "hostingsignal-web",
            "hostingsignal-daemon", "hostingsignal-monitor",
            "lsws", "postgresql", "redis-server", "postfix", "dovecot",
        ]
        statuses = {}
        for svc in services:
            try:
                import subprocess
                r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
                statuses[svc] = r.stdout.strip()
            except Exception:
                statuses[svc] = "unknown"
        return statuses


class AnomalyDetector:
    """
    Simple anomaly detection using statistical methods.
    In production, integrate ML models for better predictions.
    """

    def __init__(self):
        self.alerts: List[dict] = []

    def analyze(self, collector: MetricsCollector) -> List[dict]:
        """Analyze metrics and detect anomalies."""
        new_alerts = []

        # ── CPU spike detection ──────────────────────────────────
        if len(collector.history_cpu) >= 12:  # 1 minute of data
            recent = list(collector.history_cpu)[-12:]
            avg = sum(recent) / len(recent)
            if avg > 85:
                new_alerts.append({
                    "type": "cpu_high",
                    "severity": "critical",
                    "message": f"CPU usage critically high: {avg:.1f}% average over last minute",
                    "value": avg,
                    "threshold": 85,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif avg > 70:
                new_alerts.append({
                    "type": "cpu_elevated",
                    "severity": "warning",
                    "message": f"CPU usage elevated: {avg:.1f}% average over last minute",
                    "value": avg,
                    "threshold": 70,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # ── CPU spike prediction ─────────────────────────────────
        if len(collector.history_cpu) >= 60:
            recent_30 = list(collector.history_cpu)[-30:]
            older_30 = list(collector.history_cpu)[-60:-30]
            recent_avg = sum(recent_30) / len(recent_30)
            older_avg = sum(older_30) / len(older_30)
            if recent_avg > older_avg * 1.5 and recent_avg > 50:
                new_alerts.append({
                    "type": "cpu_spike_predicted",
                    "severity": "warning",
                    "message": f"CPU usage trending up rapidly: {older_avg:.1f}% → {recent_avg:.1f}%",
                    "predicted_peak": min(100, recent_avg * 1.3),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # ── Disk failure prediction ──────────────────────────────
        if len(collector.history_disk) >= 60:
            recent_disk = list(collector.history_disk)[-1]
            if recent_disk > 90:
                new_alerts.append({
                    "type": "disk_critical",
                    "severity": "critical",
                    "message": f"Disk usage critical: {recent_disk:.1f}% — immediate action needed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif recent_disk > 80:
                # Estimate time to full
                disk_values = list(collector.history_disk)
                if len(disk_values) > 2 and disk_values[-1] > disk_values[0]:
                    rate_per_sample = (disk_values[-1] - disk_values[0]) / len(disk_values)
                    if rate_per_sample > 0:
                        remaining = (100 - disk_values[-1]) / rate_per_sample
                        hours_to_full = (remaining * 5) / 3600  # 5 seconds per sample
                        new_alerts.append({
                            "type": "disk_filling",
                            "severity": "warning",
                            "message": f"Disk filling up: {recent_disk:.1f}%. Estimated full in {hours_to_full:.1f} hours",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

        # ── Unusual traffic detection ────────────────────────────
        if len(collector.history_net_in) >= 30:
            recent_net = list(collector.history_net_in)[-10:]
            older_net = list(collector.history_net_in)[-30:-10]
            if older_net:
                recent_delta = recent_net[-1] - recent_net[0] if len(recent_net) > 1 else 0
                older_delta = older_net[-1] - older_net[0] if len(older_net) > 1 else 1
                if older_delta > 0 and recent_delta > older_delta * 3:
                    new_alerts.append({
                        "type": "traffic_anomaly",
                        "severity": "warning",
                        "message": "Unusual network traffic spike detected — possible DDoS or scraping",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

        # ── RAM pressure ─────────────────────────────────────────
        if len(collector.history_ram) >= 6:
            recent_ram = list(collector.history_ram)[-6:]
            avg_ram = sum(recent_ram) / len(recent_ram)
            if avg_ram > 90:
                new_alerts.append({
                    "type": "ram_critical",
                    "severity": "critical",
                    "message": f"RAM usage critical: {avg_ram:.1f}% — OOM risk",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        self.alerts = new_alerts + self.alerts[:50]  # Keep last 50 alerts
        return new_alerts


class AIMonitor:
    """Main AI monitoring service."""

    def __init__(self, interval: int = 5):
        self.interval = interval
        self.collector = MetricsCollector()
        self.detector = AnomalyDetector()
        self._running = False

    async def start(self):
        """Start the AI monitoring loop."""
        self._running = True
        print("🤖 AI Monitor started")
        while self._running:
            try:
                metrics = self.collector.collect()
                alerts = self.detector.analyze(self.collector)
                if alerts:
                    for alert in alerts:
                        print(f"  🚨 [{alert['severity'].upper()}] {alert['message']}")
                await asyncio.sleep(self.interval)
            except Exception as e:
                print(f"AI Monitor error: {e}")
                await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False
        print("🤖 AI Monitor stopped")

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "alerts": self.detector.alerts[:10],
            "metrics_collected": len(self.collector.history_cpu),
        }


# Standalone run
if __name__ == "__main__":
    monitor = AIMonitor()
    asyncio.run(monitor.start())
