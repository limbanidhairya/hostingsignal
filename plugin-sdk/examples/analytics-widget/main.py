"""
Analytics Widget Plugin — Website traffic and visitor analytics for HostingSignal Panel
Parses web server access logs to provide traffic insights, bandwidth stats, and visitor data.
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("plugin.analytics_widget")
DATA_DIR = "/usr/local/hostingsignal/plugins/analytics-widget/data"
LOG_PATTERNS = [
    "/var/log/apache2/access.log",
    "/var/log/httpd/access_log",
    "/usr/local/lsws/logs/access.log",
]
APACHE_LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<uri>\S+) \S+" (?P<status>\d+) (?P<size>\d+|-)'
)


def register_hooks(event_bus):
    event_bus.on("panel.startup", on_startup, plugin_name="analytics_widget")
    event_bus.on("cron.hourly", on_hourly_aggregate, plugin_name="analytics_widget")
    logger.info("Analytics Widget plugin registered")


def on_startup(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info("Analytics Widget initialized")


def on_hourly_aggregate(data):
    """Parse access logs and aggregate stats hourly."""
    log_file = None
    for path in LOG_PATTERNS:
        if os.path.exists(path):
            log_file = path
            break

    if not log_file:
        return

    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_requests": 0,
        "unique_ips": set(),
        "status_codes": defaultdict(int),
        "bandwidth_bytes": 0,
        "top_uris": defaultdict(int),
        "methods": defaultdict(int),
    }

    try:
        with open(log_file, "r") as f:
            for line in f:
                match = APACHE_LOG_RE.match(line)
                if match:
                    stats["total_requests"] += 1
                    stats["unique_ips"].add(match.group("ip"))
                    stats["status_codes"][match.group("status")] += 1
                    stats["methods"][match.group("method")] += 1
                    size = match.group("size")
                    if size != "-":
                        stats["bandwidth_bytes"] += int(size)
                    uri = match.group("uri").split("?")[0]
                    stats["top_uris"][uri] += 1
    except Exception as e:
        logger.error(f"Error parsing access log: {e}")
        return

    stats["unique_visitors"] = len(stats["unique_ips"])
    stats["unique_ips"] = list(stats["unique_ips"])[:100]
    stats["status_codes"] = dict(stats["status_codes"])
    stats["methods"] = dict(stats["methods"])
    stats["top_uris"] = dict(sorted(stats["top_uris"].items(), key=lambda x: x[1], reverse=True)[:20])

    result_file = os.path.join(DATA_DIR, f"stats_{datetime.utcnow().strftime('%Y%m%d_%H')}.json")
    with open(result_file, "w") as f:
        json.dump(stats, f, indent=2, default=str)


def get_stats(request_data):
    """API handler: return aggregated statistics."""
    stats = []
    if os.path.exists(DATA_DIR):
        for f in sorted(os.listdir(DATA_DIR), reverse=True)[:24]:
            if f.startswith("stats_") and f.endswith(".json"):
                with open(os.path.join(DATA_DIR, f)) as fh:
                    stats.append(json.load(fh))

    total_requests = sum(s.get("total_requests", 0) for s in stats)
    total_bandwidth = sum(s.get("bandwidth_bytes", 0) for s in stats)
    total_visitors = sum(s.get("unique_visitors", 0) for s in stats)

    return {
        "period": "24h",
        "total_requests": total_requests,
        "total_bandwidth_mb": round(total_bandwidth / 1048576, 2),
        "total_unique_visitors": total_visitors,
        "hourly": stats,
    }


def get_visitors(request_data):
    """API handler: return visitor details."""
    latest_file = None
    if os.path.exists(DATA_DIR):
        files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("stats_")], reverse=True)
        if files:
            latest_file = os.path.join(DATA_DIR, files[0])

    if not latest_file:
        return {"visitors": [], "total": 0}

    with open(latest_file) as f:
        data = json.load(f)

    return {
        "unique_ips": data.get("unique_ips", []),
        "total": data.get("unique_visitors", 0),
        "top_pages": data.get("top_uris", {}),
    }


def cleanup():
    logger.info("Analytics Widget plugin unloaded")
