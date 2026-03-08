"""
AI Monitoring Microservice — Anomaly Predictor
Statistical and ML-based anomaly detection for server metrics.
Predicts: high CPU, disk failure, unusual traffic, service crashes.
"""
import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class AnomalyPredictor:
    """
    Statistical anomaly detection engine using:
    - Z-score anomaly detection
    - Moving average trend analysis
    - Exponential weighted moving average (EWMA)
    - Linear regression for trend prediction
    """

    def __init__(self):
        self.cpu_history = deque(maxlen=1440)       # 24h at 1-min intervals
        self.ram_history = deque(maxlen=1440)
        self.disk_history = deque(maxlen=1440)
        self.network_history = deque(maxlen=1440)
        self.alerts: List[dict] = []
        self.thresholds = {
            "cpu_warning": 80,
            "cpu_critical": 95,
            "ram_warning": 85,
            "ram_critical": 95,
            "disk_warning": 85,
            "disk_critical": 95,
            "network_spike_multiplier": 3.0,
            "z_score_threshold": 2.5,
        }

    def update(self, metrics: dict):
        """Feed new metrics to the predictor."""
        ts = datetime.utcnow().isoformat()

        cpu = metrics.get("cpu", {}).get("percent", 0)
        ram = metrics.get("memory", {}).get("percent", 0)
        disk_parts = metrics.get("disk", {}).get("partitions", [])
        disk = max((p.get("percent", 0) for p in disk_parts), default=0)
        net_recv = metrics.get("network", {}).get("bytes_recv", 0)

        self.cpu_history.append({"value": cpu, "ts": ts})
        self.ram_history.append({"value": ram, "ts": ts})
        self.disk_history.append({"value": disk, "ts": ts})
        self.network_history.append({"value": net_recv, "ts": ts})

        # Run all detectors
        self._detect_cpu_anomaly(cpu)
        self._detect_ram_anomaly(ram)
        self._detect_disk_failure(disk)
        self._detect_network_anomaly(net_recv)
        self._detect_service_issues(metrics.get("services", []))

    def _detect_cpu_anomaly(self, current: float):
        """Predict high CPU usage using trend analysis and thresholds."""
        if current >= self.thresholds["cpu_critical"]:
            self._add_alert("critical", "cpu_spike",
                            f"CPU usage critical: {current}%", {"value": current})
        elif current >= self.thresholds["cpu_warning"]:
            self._add_alert("warning", "cpu_high",
                            f"CPU usage high: {current}%", {"value": current})

        # Z-score detection
        values = [h["value"] for h in self.cpu_history]
        if len(values) >= 30:
            z_score = self._calculate_z_score(current, values)
            if abs(z_score) > self.thresholds["z_score_threshold"]:
                self._add_alert("warning", "cpu_anomaly",
                                f"CPU anomaly detected (z-score: {z_score:.2f})", {"z_score": z_score})

        # Trend prediction
        if len(values) >= 60:
            predicted = self._predict_next(values[-60:], steps=15)
            if predicted > self.thresholds["cpu_critical"]:
                self._add_alert("warning", "cpu_prediction",
                                f"CPU predicted to reach {predicted:.1f}% in 15 minutes",
                                {"predicted": predicted})

    def _detect_ram_anomaly(self, current: float):
        if current >= self.thresholds["ram_critical"]:
            self._add_alert("critical", "ram_critical",
                            f"RAM usage critical: {current}%", {"value": current})
        elif current >= self.thresholds["ram_warning"]:
            self._add_alert("warning", "ram_high",
                            f"RAM usage high: {current}%", {"value": current})

        # Memory leak detection — steady upward trend
        values = [h["value"] for h in self.ram_history]
        if len(values) >= 120:
            slope = self._calculate_slope(values[-120:])
            if slope > 0.1:  # Steady increase over 2 hours
                self._add_alert("warning", "memory_leak",
                                f"Potential memory leak: RAM increasing at {slope:.3f}%/min",
                                {"slope": slope})

    def _detect_disk_failure(self, current: float):
        """Predict disk full using trend extrapolation."""
        if current >= self.thresholds["disk_critical"]:
            self._add_alert("critical", "disk_full",
                            f"Disk usage critical: {current}%", {"value": current})
        elif current >= self.thresholds["disk_warning"]:
            self._add_alert("warning", "disk_high",
                            f"Disk usage high: {current}%", {"value": current})

        values = [h["value"] for h in self.disk_history]
        if len(values) >= 60:
            slope = self._calculate_slope(values[-60:])
            if slope > 0 and current > 70:
                remaining_pct = 100 - current
                minutes_to_full = remaining_pct / slope if slope > 0.001 else float("inf")
                if minutes_to_full < 1440:  # Less than 24 hours
                    hours = minutes_to_full / 60
                    self._add_alert("warning", "disk_prediction",
                                    f"Disk predicted to fill in {hours:.1f} hours at current rate",
                                    {"hours_remaining": hours, "slope": slope})

    def _detect_network_anomaly(self, current: float):
        """Detect unusual traffic spikes using EWMA."""
        values = [h["value"] for h in self.network_history]
        if len(values) < 30:
            return

        ewma = self._calculate_ewma(values[:-1], alpha=0.1)
        if ewma > 0 and current > ewma * self.thresholds["network_spike_multiplier"]:
            spike_ratio = current / ewma
            self._add_alert("warning", "traffic_spike",
                            f"Unusual traffic spike detected ({spike_ratio:.1f}x normal)",
                            {"current": current, "ewma": ewma, "spike_ratio": spike_ratio})

    def _detect_service_issues(self, services: List[dict]):
        """Detect service crashes and failures."""
        for svc in services:
            name = svc.get("name", "")
            status = svc.get("status", "")
            if status in ("failed", "inactive", "dead") and name.startswith("hostingsignal"):
                self._add_alert("critical", "service_down",
                                f"Service '{name}' is {status}", {"service": name, "status": status})

    # ─── Statistical Helpers ──────────────────────────────────────

    @staticmethod
    def _calculate_z_score(value: float, data: List[float]) -> float:
        n = len(data)
        if n < 2:
            return 0
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        std_dev = math.sqrt(variance) if variance > 0 else 1
        return (value - mean) / std_dev

    @staticmethod
    def _calculate_slope(values: List[float]) -> float:
        """Linear regression slope (change per unit time)."""
        n = len(values)
        if n < 2:
            return 0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator > 0 else 0

    @staticmethod
    def _calculate_ewma(values: List[float], alpha: float = 0.1) -> float:
        """Exponential Weighted Moving Average."""
        if not values:
            return 0
        ewma = values[0]
        for val in values[1:]:
            ewma = alpha * val + (1 - alpha) * ewma
        return ewma

    @staticmethod
    def _predict_next(values: List[float], steps: int = 1) -> float:
        """Predict future value using linear extrapolation."""
        n = len(values)
        if n < 2:
            return values[-1] if values else 0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator > 0 else 0
        intercept = y_mean - slope * x_mean
        return slope * (n + steps) + intercept

    # ─── Alert Management ──────────────────────────────────────

    def _add_alert(self, severity: str, alert_type: str, message: str, data: dict = None):
        # Dedup: don't add same alert type within 5 minutes
        now = datetime.utcnow()
        for existing in reversed(self.alerts[-20:]):
            if existing["type"] == alert_type:
                alert_time = datetime.fromisoformat(existing["timestamp"])
                if (now - alert_time).total_seconds() < 300:
                    return

        alert = {
            "id": f"{alert_type}_{now.strftime('%Y%m%d_%H%M%S')}",
            "severity": severity,
            "type": alert_type,
            "message": message,
            "data": data or {},
            "timestamp": now.isoformat(),
            "acknowledged": False,
        }
        self.alerts.append(alert)
        if len(self.alerts) > 500:
            self.alerts = self.alerts[-500:]
        logger.warning(f"[{severity.upper()}] {message}")

    def get_alerts(self, severity: str = None, limit: int = 50) -> List[dict]:
        alerts = self.alerts
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        return list(reversed(alerts[-limit:]))

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                return True
        return False

    def get_predictions(self) -> dict:
        """Get current predictions for all metrics."""
        predictions = {}

        cpu_values = [h["value"] for h in self.cpu_history]
        if len(cpu_values) >= 30:
            predictions["cpu_15m"] = round(self._predict_next(cpu_values[-60:], 15), 1)
            predictions["cpu_60m"] = round(self._predict_next(cpu_values[-60:], 60), 1)

        ram_values = [h["value"] for h in self.ram_history]
        if len(ram_values) >= 30:
            predictions["ram_15m"] = round(self._predict_next(ram_values[-60:], 15), 1)

        disk_values = [h["value"] for h in self.disk_history]
        if len(disk_values) >= 30:
            slope = self._calculate_slope(disk_values[-60:])
            current = disk_values[-1]
            if slope > 0 and current > 50:
                remaining = 100 - current
                hours_to_full = (remaining / slope / 60)
                predictions["disk_hours_to_full"] = round(hours_to_full, 1)

        return predictions

    def get_health_score(self) -> dict:
        """Calculate overall system health score (0-100)."""
        scores = []

        cpu_vals = [h["value"] for h in self.cpu_history][-10:]
        if cpu_vals:
            avg_cpu = sum(cpu_vals) / len(cpu_vals)
            scores.append(max(0, 100 - avg_cpu))

        ram_vals = [h["value"] for h in self.ram_history][-10:]
        if ram_vals:
            avg_ram = sum(ram_vals) / len(ram_vals)
            scores.append(max(0, 100 - avg_ram))

        disk_vals = [h["value"] for h in self.disk_history][-5:]
        if disk_vals:
            avg_disk = sum(disk_vals) / len(disk_vals)
            scores.append(max(0, 100 - avg_disk))

        unacked_alerts = sum(1 for a in self.alerts[-50:] if not a["acknowledged"])
        alert_penalty = min(unacked_alerts * 5, 30)

        overall = (sum(scores) / len(scores) if scores else 100) - alert_penalty
        overall = max(0, min(100, overall))

        return {
            "score": round(overall),
            "status": "healthy" if overall >= 70 else "degraded" if overall >= 40 else "critical",
            "unacknowledged_alerts": unacked_alerts,
        }


# Singleton
anomaly_predictor = AnomalyPredictor()
