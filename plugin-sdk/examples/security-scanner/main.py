"""
Security Scanner Plugin — ClamAV integration for HostingSignal Panel
Automatically scans uploaded files and website directories for malware.
"""
import os
import subprocess
import json
import logging
from datetime import datetime

logger = logging.getLogger("plugin.security_scanner")
SCAN_RESULTS_DIR = "/usr/local/hostingsignal/plugins/security-scanner/results"
WEBSITE_ROOT = "/home"


def register_hooks(event_bus):
    """Called when plugin is loaded — register event handlers."""
    event_bus.on("website.created", on_website_created, plugin_name="security_scanner")
    event_bus.on("cron.daily", on_daily_scan, plugin_name="security_scanner")
    event_bus.on("panel.startup", on_startup, plugin_name="security_scanner")
    logger.info("Security Scanner plugin registered")


def on_startup(data):
    """Initialize plugin on panel startup."""
    os.makedirs(SCAN_RESULTS_DIR, exist_ok=True)
    logger.info("Security Scanner initialized")


def on_website_created(data):
    """Scan new website directory on creation."""
    domain = data.get("domain", "")
    if not domain:
        return
    website_path = os.path.join(WEBSITE_ROOT, domain, "public_html")
    if os.path.exists(website_path):
        _run_scan(website_path, domain)


def on_daily_scan(data):
    """Run full scan on all website directories daily."""
    if not os.path.exists(WEBSITE_ROOT):
        return
    for domain_dir in os.listdir(WEBSITE_ROOT):
        website_path = os.path.join(WEBSITE_ROOT, domain_dir, "public_html")
        if os.path.isdir(website_path):
            _run_scan(website_path, domain_dir)


def _run_scan(path, domain):
    """Execute ClamAV scan on given path."""
    try:
        result = subprocess.run(
            ["clamscan", "-r", "--infected", "--no-summary", path],
            capture_output=True, text=True, timeout=600
        )
        infected_files = []
        for line in result.stdout.strip().split("\n"):
            if "FOUND" in line:
                parts = line.split(":")
                infected_files.append({
                    "file": parts[0].strip(),
                    "threat": parts[1].strip().replace("FOUND", "").strip() if len(parts) > 1 else "Unknown",
                })

        scan_result = {
            "domain": domain,
            "path": path,
            "scanned_at": datetime.utcnow().isoformat(),
            "total_infected": len(infected_files),
            "infected_files": infected_files,
            "return_code": result.returncode,
        }

        result_file = os.path.join(SCAN_RESULTS_DIR, f"{domain}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        with open(result_file, "w") as f:
            json.dump(scan_result, f, indent=2)

        if infected_files:
            logger.warning(f"[{domain}] Found {len(infected_files)} infected files!")
        else:
            logger.info(f"[{domain}] Clean — no threats detected")

        return scan_result
    except FileNotFoundError:
        logger.error("ClamAV (clamscan) is not installed. Install with: apt install clamav")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"Scan timeout for {path}")
        return None


def start_scan(request_data):
    """API handler: start a manual scan."""
    path = request_data.get("path", "")
    domain = request_data.get("domain", "unknown")
    if not os.path.exists(path):
        return {"error": f"Path not found: {path}"}
    return _run_scan(path, domain)


def get_results(request_data):
    """API handler: get scan results."""
    results = []
    if os.path.exists(SCAN_RESULTS_DIR):
        for f in sorted(os.listdir(SCAN_RESULTS_DIR), reverse=True)[:50]:
            if f.endswith(".json"):
                with open(os.path.join(SCAN_RESULTS_DIR, f)) as fh:
                    results.append(json.load(fh))
    return {"results": results}


def get_status(request_data):
    """API handler: get scanner status."""
    try:
        result = subprocess.run(["clamscan", "--version"], capture_output=True, text=True, timeout=10)
        clamav_version = result.stdout.strip()
        installed = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        clamav_version = "Not installed"
        installed = False

    return {
        "installed": installed,
        "clamav_version": clamav_version,
        "results_dir": SCAN_RESULTS_DIR,
    }


def cleanup():
    """Called when plugin is unloaded."""
    logger.info("Security Scanner plugin unloaded")
