"""
HostingSignal — OpenLiteSpeed Web Server Manager
Virtual host creation, PHP version management, server control.
"""
import os
from .server_utils import run_cmd, write_file, read_file, ensure_dir, DEV_MODE, logger

# Paths
OLS_ROOT = "/usr/local/lsws"
VHOST_DIR = f"{OLS_ROOT}/conf/vhosts"
VHOST_TEMPLATE = f"{OLS_ROOT}/conf/templates"
WEB_ROOT = "/home"

# Demo data for dev mode
DEMO_WEBSITES = [
    {"domain": "example.com", "doc_root": "/home/example.com/public_html", "php": "8.2", "ssl": True, "status": "active"},
    {"domain": "blog.example.com", "doc_root": "/home/blog.example.com/public_html", "php": "8.1", "ssl": True, "status": "active"},
    {"domain": "shop.mysite.com", "doc_root": "/home/shop.mysite.com/public_html", "php": "8.2", "ssl": False, "status": "active"},
]


def list_websites() -> list[dict]:
    """List all configured virtual hosts."""
    if DEV_MODE:
        return DEMO_WEBSITES
    result = run_cmd(f"ls {VHOST_DIR}")
    if not result.success:
        return []
    sites = []
    for domain in result.stdout.strip().split("\n"):
        domain = domain.strip()
        if not domain:
            continue
        doc_root = f"{WEB_ROOT}/{domain}/public_html"
        conf = read_file(f"{VHOST_DIR}/{domain}/vhconf.conf") or ""
        php_ver = "8.2"
        for line in conf.split("\n"):
            if "lsphp" in line:
                parts = line.split("lsphp")
                if len(parts) > 1:
                    php_ver = parts[1][:2]
                    php_ver = f"{php_ver[0]}.{php_ver[1]}"
                break
        ssl = os.path.exists(f"/etc/letsencrypt/live/{domain}/fullchain.pem") if not DEV_MODE else False
        sites.append({"domain": domain, "doc_root": doc_root, "php": php_ver, "ssl": ssl, "status": "active"})
    return sites


def create_website(domain: str, php_version: str = "8.2", owner: str = "nobody") -> dict:
    """Create a new virtual host with document root."""
    doc_root = f"{WEB_ROOT}/{domain}/public_html"
    log_dir = f"{WEB_ROOT}/{domain}/logs"
    ensure_dir(doc_root)
    ensure_dir(log_dir)

    # Create vhost config
    vhost_conf = f"""docRoot                   {doc_root}
vhDomain                  {domain}
vhAliases                 www.{domain}
enableGzip                1
enableBr                  1

index {{
  useServer               0
  indexFiles               index.php, index.html
}}

scripthandler {{
  add                     lsapi:lsphp{php_version.replace('.', '')} php
}}

extprocessor lsphp{php_version.replace('.', '')} {{
  type                    lsapi
  address                 uds://tmp/lshttpd/{domain}.sock
  maxConns                10
  env                     PHP_LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  pcKeepAliveTimeout      1
  respBuffer              0
  autoStart               2
  path                    /usr/local/lsws/lsphp{php_version.replace('.', '')}/bin/lsphp
  backlog                 100
  instances               1
  extUser                 {owner}
  extGroup                {owner}
  runOnStartUp            2
  priority                0
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           1400
  procHardLimit           1500
}}

accesslog {log_dir}/access.log {{
  useServer               0
  logFormat               "%h %l %u %t \\"%r\\" %>s %b"
  logHeaders              5
  rollingSize             100M
}}

errorlog {log_dir}/error.log {{
  useServer               0
  logLevel                WARN
  rollingSize             10M
}}
"""
    conf_dir = f"{VHOST_DIR}/{domain}"
    ensure_dir(conf_dir)
    write_file(f"{conf_dir}/vhconf.conf", vhost_conf)

    # Create index page
    index_html = f"""<!DOCTYPE html>
<html><head><title>Welcome to {domain}</title></head>
<body><h1>{domain}</h1><p>Hosted by HostingSignal</p></body></html>
"""
    write_file(f"{doc_root}/index.html", index_html, backup=False)

    # Add vhost to OLS main config
    listener_entry = f"""
virtualhost {domain} {{
  vhRoot                  {WEB_ROOT}/{domain}
  configFile              {conf_dir}/vhconf.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
}}
"""
    run_cmd(f"echo '{listener_entry}' >> {OLS_ROOT}/conf/httpd_config.conf")

    # Set permissions
    run_cmd(f"chown -R {owner}:{owner} {WEB_ROOT}/{domain}")
    run_cmd(f"chmod -R 755 {doc_root}")

    # Restart OLS
    restart_webserver()

    return {"domain": domain, "doc_root": doc_root, "php": php_version, "ssl": False, "status": "active"}


def delete_website(domain: str) -> bool:
    """Remove a virtual host and its data."""
    run_cmd(f"rm -rf {VHOST_DIR}/{domain}")
    run_cmd(f"rm -rf {WEB_ROOT}/{domain}")
    # Remove from httpd_config (sed)
    run_cmd(f"sed -i '/virtualhost {domain}/,/}}/d' {OLS_ROOT}/conf/httpd_config.conf")
    restart_webserver()
    return True


def change_php_version(domain: str, version: str) -> bool:
    """Change PHP version for a virtual host."""
    conf_path = f"{VHOST_DIR}/{domain}/vhconf.conf"
    conf = read_file(conf_path)
    if not conf:
        return False
    # Replace lsphp references
    import re
    conf = re.sub(r'lsphp\d+', f'lsphp{version.replace(".", "")}', conf)
    write_file(conf_path, conf)
    restart_webserver()
    return True


def restart_webserver() -> bool:
    result = run_cmd(f"{OLS_ROOT}/bin/lswsctrl restart")
    return result.success


def stop_webserver() -> bool:
    result = run_cmd(f"{OLS_ROOT}/bin/lswsctrl stop")
    return result.success


def webserver_status() -> dict:
    if DEV_MODE:
        return {"running": True, "version": "1.7.19", "uptime": "3d 14h 22m", "connections": 47}
    result = run_cmd(f"{OLS_ROOT}/bin/lswsctrl status")
    running = "running" in result.stdout.lower() if result.success else False
    return {"running": running, "output": result.stdout}
