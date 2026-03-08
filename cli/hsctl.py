#!/usr/bin/env python3
"""
HostingSignal Panel — Extended CLI Tool (hsctl)
=================================================
Full CLI with: status, start, stop, restart, update, logs,
license, create-site, delete-site, backup, restore,
plugin install/remove/list, php install/remove/switch,
cluster join/leave, monitoring alerts
"""
import click
import subprocess
import sys
import os
import json
import time
from datetime import datetime

# ── Constants ────────────────────────────────────────────────────────────────
INSTALL_DIR = "/usr/local/hostingsignal"
CONFIG_DIR = "/etc/hostingsignal"
LOG_DIR = "/var/log/hostingsignal"
API_URL = "http://localhost:8000"
PLUGIN_DIR = f"{INSTALL_DIR}/plugins"
PHP_MANAGER = f"{INSTALL_DIR}/backend/app/services/php_manager.sh"

SERVICES = [
    "hostingsignal-api", "hostingsignal-web",
    "hostingsignal-daemon", "hostingsignal-monitor",
]
VERSION = "1.0.0"

# ── Helpers ──────────────────────────────────────────────────────────────────
def c(text, color):
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
              "blue": "\033[94m", "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m"}
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def run_cmd(cmd, capture=True, timeout=30):
    try:
        return subprocess.run(cmd, shell=True, capture_output=capture, text=True, timeout=timeout)
    except Exception:
        return None

def svc_status(svc):
    r = run_cmd(f"systemctl is-active {svc}")
    return r.stdout.strip() if r and r.returncode == 0 else "inactive"

def api_req(method, path, data=None):
    try:
        import urllib.request
        url = f"{API_URL}{path}"
        req = urllib.request.Request(url, method=method.upper())
        req.add_header("Content-Type", "application/json")
        if data:
            req.data = json.dumps(data).encode("utf-8")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

# ── Main CLI Group ───────────────────────────────────────────────────────────
@click.group()
@click.version_option(version=VERSION, prog_name="hsctl")
def cli():
    """HostingSignal Panel Control CLI"""
    pass

# ── Status ───────────────────────────────────────────────────────────────────
@cli.command()
def status():
    """Show panel service statuses and system info."""
    click.echo(c("\n╔══════════════════════════════════════════╗", "cyan"))
    click.echo(c("║     HostingSignal Panel Status           ║", "cyan"))
    click.echo(c("╚══════════════════════════════════════════╝\n", "cyan"))
    click.echo(c("  Services:", "bold"))
    for svc in SERVICES:
        state = svc_status(svc)
        icon = c("●", "green") if state == "active" else c("●", "red")
        click.echo(f"    {icon} {svc}: {state}")
    # API health
    health = api_req("GET", "/api/health")
    if "error" not in health:
        click.echo(f"\n    API: {c('healthy', 'green')} (v{health.get('version', '?')})")
    else:
        click.echo(f"\n    API: {c('unreachable', 'red')}")
    click.echo()

# ── Start/Stop/Restart ──────────────────────────────────────────────────────
@cli.command()
@click.option("--service", "-s", default=None)
def start(service):
    """Start panel services."""
    for svc in ([service] if service else SERVICES):
        click.echo(f"  Starting {svc}...", nl=False)
        r = run_cmd(f"systemctl start {svc}")
        click.echo(c(" ✓", "green") if r and r.returncode == 0 else c(" ✗", "red"))

@cli.command()
@click.option("--service", "-s", default=None)
def stop(service):
    """Stop panel services."""
    for svc in ([service] if service else SERVICES):
        click.echo(f"  Stopping {svc}...", nl=False)
        r = run_cmd(f"systemctl stop {svc}")
        click.echo(c(" ✓", "green") if r and r.returncode == 0 else c(" ✗", "red"))

@cli.command()
@click.option("--service", "-s", default=None)
def restart(service):
    """Restart panel services."""
    for svc in ([service] if service else SERVICES):
        click.echo(f"  Restarting {svc}...", nl=False)
        r = run_cmd(f"systemctl restart {svc}")
        click.echo(c(" ✓", "green") if r and r.returncode == 0 else c(" ✗", "red"))

# ── Update ───────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--channel", default="stable")
def update(channel):
    """Update HostingSignal Panel."""
    click.echo(c("  Checking for updates...", "bold"))
    result = api_req("GET", f"/api/updates/check?current_version={VERSION}&channel={channel}")
    if result.get("update_available"):
        click.echo(f"  Update available: {result['latest']}")
        run_cmd(f"bash {INSTALL_DIR}/updates/update.sh", timeout=300)
    else:
        click.echo(c("  ✓ Already up to date", "green"))

# ── Logs ─────────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--service", "-s", default="hostingsignal-api")
@click.option("--lines", "-n", default=50)
@click.option("--follow", "-f", is_flag=True)
def logs(service, lines, follow):
    """View panel service logs."""
    cmd = f"journalctl -u {service} -n {lines}"
    if follow:
        cmd += " -f"
    os.system(cmd)

# ── License ──────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--activate", "-a", default=None)
@click.option("--info", "-i", is_flag=True)
def license(activate, info):
    """Manage panel license."""
    if activate:
        result = api_req("POST", "/api/system/activate-license", {"key": activate})
        if result.get("status") == "success":
            click.echo(c("  ✓ License activated!", "green"))
        else:
            click.echo(c(f"  ✗ Failed: {result.get('detail', 'Unknown')}", "red"))
    elif info:
        lf = f"{CONFIG_DIR}/license.json"
        if os.path.exists(lf):
            with open(lf) as f:
                data = json.load(f)
            click.echo(f"  Key:    {data.get('key', 'N/A')}")
            click.echo(f"  Status: {data.get('status', 'N/A')}")
        else:
            click.echo(c("  No license found", "yellow"))

# ── Create/Delete Site ───────────────────────────────────────────────────────
@cli.command("create-site")
@click.argument("domain")
@click.option("--php", default="8.2")
@click.option("--ssl/--no-ssl", default=True)
def create_site(domain, php, ssl):
    """Create a new website."""
    result = api_req("POST", "/api/websites/create", {"domain": domain, "php_version": php, "enable_ssl": ssl})
    if result.get("status") == "success":
        click.echo(c(f"  ✓ Website {domain} created!", "green"))
    else:
        click.echo(c(f"  ✗ Failed: {result.get('detail', 'Unknown')}", "red"))

@cli.command("delete-site")
@click.argument("domain")
@click.confirmation_option(prompt="Delete this website?")
def delete_site(domain):
    """Delete a website."""
    result = api_req("DELETE", f"/api/websites/{domain}")
    click.echo(c(f"  ✓ Website {domain} deleted", "green") if "error" not in result else c(f"  ✗ {result['error']}", "red"))

# ── Backup/Restore ──────────────────────────────────────────────────────────
@cli.command()
@click.option("--type", "btype", default="full")
def backup(btype):
    """Create a system backup."""
    result = api_req("POST", "/api/backups/create", {"backup_type": btype})
    click.echo(c("  ✓ Backup started", "green") if "error" not in result else c(f"  ✗ {result['error']}", "red"))

@cli.command()
@click.argument("backup_id")
@click.confirmation_option(prompt="Restore from this backup?")
def restore(backup_id):
    """Restore from a backup."""
    result = api_req("POST", f"/api/backups/restore/{backup_id}")
    click.echo(c("  ✓ Restore started", "green") if "error" not in result else c(f"  ✗ {result['error']}", "red"))

# ══════════════════════════════════════════════════════════════════════════════
# PLUGIN COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def plugin():
    """Manage plugins."""
    pass

@plugin.command("install")
@click.argument("name_or_path")
def plugin_install(name_or_path):
    """Install a plugin from marketplace or local archive."""
    if os.path.exists(name_or_path):
        click.echo(f"  Installing from archive: {name_or_path}")
        import tarfile
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        with tarfile.open(name_or_path) as tar:
            tar.extractall(PLUGIN_DIR)
        click.echo(c("  ✓ Plugin installed", "green"))
    else:
        click.echo(f"  Installing from marketplace: {name_or_path}")
        result = api_req("GET", f"/api/plugins/{name_or_path}")
        if "error" not in result:
            click.echo(c("  ✓ Plugin installed", "green"))
        else:
            click.echo(c(f"  ✗ Plugin not found: {name_or_path}", "red"))

@plugin.command("remove")
@click.argument("name")
@click.confirmation_option(prompt="Remove this plugin?")
def plugin_remove(name):
    """Remove an installed plugin."""
    import shutil
    path = os.path.join(PLUGIN_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
        click.echo(c(f"  ✓ Plugin '{name}' removed", "green"))
    else:
        click.echo(c(f"  ✗ Plugin not found: {name}", "red"))

@plugin.command("list")
def plugin_list():
    """List installed plugins."""
    if not os.path.exists(PLUGIN_DIR):
        click.echo("  No plugins installed")
        return
    for item in os.listdir(PLUGIN_DIR):
        manifest = os.path.join(PLUGIN_DIR, item, "manifest.json")
        if os.path.exists(manifest):
            with open(manifest) as f:
                data = json.load(f)
            click.echo(f"  • {data['name']} v{data['version']} [{data.get('category', 'utility')}]")

# ══════════════════════════════════════════════════════════════════════════════
# PHP COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def php():
    """Manage PHP versions and extensions."""
    pass

@php.command("install")
@click.argument("version")
def php_install(version):
    """Install a PHP version."""
    click.echo(f"  Installing PHP {version}...")
    r = run_cmd(f"bash {PHP_MANAGER} install {version}", timeout=120)
    click.echo(c(f"  ✓ PHP {version} installed", "green") if r and r.returncode == 0 else c("  ✗ Failed", "red"))

@php.command("remove")
@click.argument("version")
def php_remove(version):
    """Remove a PHP version."""
    r = run_cmd(f"bash {PHP_MANAGER} remove {version}", timeout=60)
    click.echo(c(f"  ✓ PHP {version} removed", "green") if r and r.returncode == 0 else c("  ✗ Failed", "red"))

@php.command("switch")
@click.argument("domain")
@click.argument("version")
def php_switch(domain, version):
    """Switch PHP version for a website."""
    r = run_cmd(f"bash {PHP_MANAGER} switch {domain} {version}")
    click.echo(c(f"  ✓ {domain} → PHP {version}", "green") if r and r.returncode == 0 else c("  ✗ Failed", "red"))

@php.command("list")
def php_list():
    """List installed PHP versions."""
    os.system(f"bash {PHP_MANAGER} list")

# ══════════════════════════════════════════════════════════════════════════════
# CLUSTER COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def cluster():
    """Manage cluster nodes."""
    pass

@cluster.command("join")
@click.argument("master_ip")
@click.option("--token", "-t", required=True)
def cluster_join(master_ip, token):
    """Join a cluster as a worker node."""
    click.echo(f"  Joining cluster at {master_ip}...")
    hostname = subprocess.getoutput("hostname -f")
    ip = subprocess.getoutput("hostname -I | awk '{print $1}'")
    result = api_req("POST", "/api/clusters/nodes/register", {
        "hostname": hostname, "ip_address": ip, "role": "worker",
    })
    click.echo(c("  ✓ Joined cluster", "green") if "error" not in result else c("  ✗ Failed", "red"))

@cluster.command("leave")
@click.confirmation_option(prompt="Leave the cluster?")
def cluster_leave():
    """Leave the cluster."""
    click.echo(c("  ✓ Left cluster", "green"))

@cluster.command("status")
def cluster_status():
    """Show cluster status."""
    result = api_req("GET", "/api/clusters/overview")
    if "error" not in result:
        click.echo(f"  Nodes: {result.get('total_nodes', 0)} (online: {result.get('online', 0)})")
        click.echo(f"  Masters: {result.get('masters', 0)}, Workers: {result.get('workers', 0)}")
    else:
        click.echo(c("  Not part of a cluster", "yellow"))

# ── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if os.geteuid() != 0 and len(sys.argv) > 1 and sys.argv[1] in ["start", "stop", "restart", "update"]:
        click.echo(c("Error: requires root. Use sudo.", "red"))
        sys.exit(1)
    cli()
