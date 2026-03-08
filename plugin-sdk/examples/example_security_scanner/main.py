"""
Example Plugin: Security Scanner
=================================
Demonstrates the HostingSignal Plugin SDK.
Scans websites for common security issues.
"""
import subprocess
from datetime import datetime, timezone

_scan_results = {}


def register_hooks(event_bus):
    """Called by the plugin loader — register event hooks here."""
    event_bus.on("website.created", on_website_created)
    event_bus.on("cron.daily", on_daily_cron)
    print("  🔍 Security Scanner plugin hooks registered")


def on_website_created(data):
    """Auto-scan new websites."""
    domain = data.get("domain") if isinstance(data, dict) else str(data)
    print(f"  🔍 Auto-scanning new website: {domain}")
    scan_website(domain)


def on_daily_cron(data):
    """Run daily scan on all known websites."""
    for domain in list(_scan_results.keys()):
        scan_website(domain)


def scan_website(domain: str) -> dict:
    """Perform a security scan on a domain."""
    results = {
        "domain": domain,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "score": 100,
    }

    # Check SSL
    try:
        r = subprocess.run(["openssl", "s_client", "-connect", f"{domain}:443", "-brief"],
                           capture_output=True, text=True, timeout=10)
        ssl_ok = r.returncode == 0
    except Exception:
        ssl_ok = False
    results["checks"].append({"name": "SSL Certificate", "passed": ssl_ok, "severity": "critical"})
    if not ssl_ok:
        results["score"] -= 30

    # Check HTTP headers
    try:
        r = subprocess.run(["curl", "-sI", f"https://{domain}", "--max-time", "5"],
                           capture_output=True, text=True, timeout=10)
        headers = r.stdout.lower()
        has_hsts = "strict-transport-security" in headers
        has_xfo = "x-frame-options" in headers
        has_csp = "content-security-policy" in headers
    except Exception:
        has_hsts = has_xfo = has_csp = False

    results["checks"].append({"name": "HSTS Header", "passed": has_hsts, "severity": "medium"})
    results["checks"].append({"name": "X-Frame-Options", "passed": has_xfo, "severity": "medium"})
    results["checks"].append({"name": "Content-Security-Policy", "passed": has_csp, "severity": "low"})
    if not has_hsts:
        results["score"] -= 15
    if not has_xfo:
        results["score"] -= 10
    if not has_csp:
        results["score"] -= 5

    results["score"] = max(0, results["score"])
    _scan_results[domain] = results
    return results


def get_results() -> list:
    """Get all scan results."""
    return list(_scan_results.values())


def cleanup():
    """Called when the plugin is unloaded."""
    _scan_results.clear()
    print("  🔍 Security Scanner plugin cleaned up")
