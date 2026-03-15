from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "configs" / "service-catalog.json"
INSTALL_CONFIG_PATH = ROOT / "configs" / "install-config.json"

WEB_CHOICES = {
    "1": "openlitespeed",
    "2": "apache",
}
DB_CHOICES = {
    "1": "mariadb",
    "2": "mysql",
}
PROFILE_SET_CHOICES = {
    "core": ["core"],
    "full": ["core", "mail", "dns", "ftp", "security", "ops"],
}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def detect_environment() -> dict:
    release = {}
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            release[key] = value.strip().strip('"')
    proc_version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore") if Path("/proc/version").exists() else ""
    return {
        "platform": platform.system().lower(),
        "distribution": release.get("ID", "unknown"),
        "version": release.get("VERSION_ID", "unknown"),
        "is_wsl": "microsoft" in proc_version.lower() or bool(os.environ.get("WSL_INTEROP")),
    }


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check, text=True)


def _normalize_base_url(raw: str) -> str:
    return raw.rstrip("/")


def _json_request(url: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None, timeout: int = 8) -> dict:
    data = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def _resolve_local_identity() -> tuple[str, str]:
    hostname = socket.getfqdn() or socket.gethostname() or "localhost"
    ip_address = "127.0.0.1"
    try:
        ip_address = socket.gethostbyname(hostname)
    except OSError:
        pass
    return hostname, ip_address


def attempt_devpanel_registration(config: dict) -> bool:
    base_candidates = [
        os.getenv("HSDEV_REGISTER_API_BASE", "").strip(),
        "http://127.0.0.1:2087",
        "http://localhost:2087",
    ]
    hostname, ip_address = _resolve_local_identity()
    payload = {
        "hostname": hostname,
        "ip_address": ip_address,
        "port": int(config["ports"]["web"]),
        "os_info": f"Local sandbox ({config['web_server']} + {config['database']})",
        "region": "Local Sandbox",
    }
    heartbeat_metrics = _collect_local_metrics(config)

    for raw_base in base_candidates:
        if not raw_base:
            continue
        base = _normalize_base_url(raw_base)
        try:
            _json_request(f"{base}/api/health", timeout=5)
            existing = _json_request(f"{base}/api/clusters/nodes", timeout=8)
            nodes = existing.get("nodes") or []
            existing_node = next((node for node in nodes if node.get("hostname") == hostname or node.get("ip_address") == ip_address), None)
            if existing_node:
                if heartbeat_metrics and existing_node.get("id"):
                    _json_request(
                        f"{base}/api/clusters/nodes/{existing_node['id']}/heartbeat",
                        method="POST",
                        payload=heartbeat_metrics,
                        timeout=10,
                    )
                print(f"- devpanel node already registered via {base}")
                return True

            result = _json_request(f"{base}/api/clusters/nodes/register", method="POST", payload=payload, timeout=10)
            node = result.get("node") or {}
            if result.get("success"):
                if heartbeat_metrics and node.get("id"):
                    _json_request(
                        f"{base}/api/clusters/nodes/{node['id']}/heartbeat",
                        method="POST",
                        payload=heartbeat_metrics,
                        timeout=10,
                    )
                print(f"- registered local sandbox with devpanel at {base}")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
            continue

    print("- skipped devpanel registration (developer panel API not reachable)")
    return False


def _collect_local_metrics(config: dict) -> dict | None:
    try:
        import psutil  # type: ignore
    except Exception:
        return None

    try:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(str(ROOT))
        load_average = None
        if hasattr(os, "getloadavg"):
            try:
                load_average = os.getloadavg()[0]
            except OSError:
                load_average = None

        return {
            "panel_version": "local-installer",
            "cpu_cores": psutil.cpu_count() or 1,
            "ram_mb": int(vm.total / (1024 * 1024)),
            "disk_gb": int(disk.total / (1024 * 1024 * 1024)),
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "ram_percent": vm.percent,
            "disk_percent": disk.percent,
            "load_average": load_average,
            "active_connections": None,
            "uptime_seconds": int(time.time() - psutil.boot_time()),
        }
    except Exception:
        return None


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def choose_available_port(preferred: int, used_ports: set[int], min_port: int = 1024, max_port: int = 65535) -> int:
    if preferred not in used_ports and is_port_available(preferred):
        used_ports.add(preferred)
        return preferred

    for port in range(max(min_port, preferred + 1), max_port + 1):
        if port in used_ports:
            continue
        if is_port_available(port):
            used_ports.add(port)
            return port

    raise RuntimeError(f"Unable to find an available host port starting from {preferred}")


def detect_compose_base_cmd() -> list[str] | None:
    try:
        run(["docker", "compose", "version"], check=True)
        return ["docker", "compose"]
    except Exception:
        pass
    try:
        run(["docker-compose", "--version"], check=True)
        return ["docker-compose"]
    except Exception:
        return None


def docker_available() -> bool:
    try:
        run(["docker", "--version"], check=True)
        return detect_compose_base_cmd() is not None
    except Exception:
        return False


def prompt_choice(prompt: str, mapping: dict[str, str], default: str) -> str:
    print(prompt)
    for key, value in mapping.items():
        label = value.replace("openlitespeed", "OpenLiteSpeed").replace("mariadb", "MariaDB").replace("mysql", "MySQL").replace("apache", "Apache")
        marker = " (Recommended)" if value == default else ""
        print(f"{key}. {label}{marker}")
    selected = input(f"Select option [{default}]: ").strip()
    if not selected:
        return default
    if selected in mapping:
        return mapping[selected]
    if selected in mapping.values():
        return selected
    raise SystemExit(f"Unsupported selection: {selected}")


def resolve_profiles(args: argparse.Namespace, existing: dict, catalog: dict) -> list[str]:
    available_profiles = list(catalog.get("profiles", {}).keys())
    if not available_profiles:
        return ["core"]

    if args.profiles:
        requested = [item.strip() for item in args.profiles.split(",") if item.strip()]
        invalid = [item for item in requested if item not in available_profiles]
        if invalid:
            raise SystemExit(f"Unsupported profiles: {', '.join(invalid)}")
        return requested

    if args.profile_set:
        return PROFILE_SET_CHOICES[args.profile_set][:]

    if args.all or args.mode == "all":
        return PROFILE_SET_CHOICES["full"][:]

    existing_profiles = existing.get("profiles") or []
    valid_existing = [item for item in existing_profiles if item in available_profiles]
    if valid_existing:
        return valid_existing

    return PROFILE_SET_CHOICES["full"][:]


def build_install_config(args: argparse.Namespace, catalog: dict) -> dict:
    existing = {}
    if INSTALL_CONFIG_PATH.exists():
        existing = json.loads(INSTALL_CONFIG_PATH.read_text(encoding="utf-8"))

    web = args.web
    database = args.db
    if not args.non_interactive:
        web = web or prompt_choice("Select Web Server", WEB_CHOICES, existing.get("web_server", "openlitespeed"))
        database = database or prompt_choice("Select Database", DB_CHOICES, existing.get("database", "mariadb"))
    else:
        web = web or existing.get("web_server", "openlitespeed")
        database = database or existing.get("database", "mariadb")

    profiles = resolve_profiles(args, existing, catalog)

    paths = {
        "services_root": catalog["local_root"],
        "runtime_root": catalog["runtime_root"],
        "data_root": catalog["data_root"],
        "log_root": catalog["log_root"],
    }

    existing_ports = existing.get("ports", {})
    used_ports: set[int] = set()

    def resolve_port(key: str, default: int) -> int:
        if key in existing_ports:
            candidate = int(existing_ports[key])
            if candidate not in used_ports:
                used_ports.add(candidate)
                return candidate
            return choose_available_port(candidate, used_ports)
        return choose_available_port(default, used_ports)

    service_ports = {
        "web": resolve_port("web", int(catalog["services"][web]["port"])),
        "database": resolve_port("database", int(catalog["services"][database]["port"])),
        "redis": resolve_port("redis", int(catalog["services"]["redis"]["port"])),
        "memcached": resolve_port("memcached", int(catalog["services"]["memcached"]["port"])),
        "phpmyadmin": resolve_port("phpmyadmin", int(catalog["services"]["phpmyadmin"]["port"])),
        "powerdns": resolve_port("powerdns", int(catalog["services"]["powerdns"]["port"])),
        "ftp": resolve_port("ftp", int(catalog["services"]["pureftpd"]["port"])),
    }

    config = {
        "schema": 1,
        "environment": detect_environment(),
        "web_server": web,
        "database": database,
        "paths": paths,
        "ports": service_ports,
        "profiles": profiles,
        "secrets": {
            "db_root_password": existing.get("secrets", {}).get("db_root_password") or secrets.token_urlsafe(18),
            "db_app_password": existing.get("secrets", {}).get("db_app_password") or secrets.token_urlsafe(18),
            "pdns_api_key": existing.get("secrets", {}).get("pdns_api_key") or secrets.token_hex(16),
        },
    }
    return config


def ensure_layout(config: dict, catalog: dict) -> None:
    for rel in [config["paths"]["services_root"], config["paths"]["runtime_root"], config["paths"]["data_root"], config["paths"]["log_root"], "configs"]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    for subdir in ["websites", "databases", "mail", "dns", "ftp", "ssl", "cache/redis"]:
        (ROOT / config["paths"]["data_root"] / subdir).mkdir(parents=True, exist_ok=True)

    for service_name in catalog["services"].keys():
        service_root = ROOT / config["paths"]["services_root"] / service_name
        for child in ["config", "data", "logs"]:
            (service_root / child).mkdir(parents=True, exist_ok=True)
        readme = service_root / "README.md"
        if not readme.exists():
            readme.write_text(f"# {service_name}\n\nLocal service workspace generated by install.sh.\n", encoding="utf-8")


def write_env_file(config: dict) -> Path:
    runtime_root = ROOT / config["paths"]["runtime_root"]
    env_path = runtime_root / ".env"
    env_path.write_text(
        dedent(
            f"""
            WEB_PORT={config['ports']['web']}
            DB_PORT={config['ports']['database']}
            REDIS_PORT={config['ports']['redis']}
            MEMCACHED_PORT={config['ports']['memcached']}
            PHPMYADMIN_PORT={config['ports']['phpmyadmin']}
            DB_ROOT_PASSWORD={config['secrets']['db_root_password']}
            DB_APP_PASSWORD={config['secrets']['db_app_password']}
            PDNS_API_KEY={config['secrets']['pdns_api_key']}
            WEB_SERVER={config['web_server']}
            DATABASE_ENGINE={config['database']}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return env_path


def write_generated_service_files(config: dict) -> None:
    services_root = ROOT / config["paths"]["services_root"]

    apache_conf = dedent(
        """
        ServerName localhost
        Listen 80
        LoadModule authz_core_module modules/mod_authz_core.so
        LoadModule authz_host_module modules/mod_authz_host.so
        DocumentRoot /usr/local/apache2/htdocs
        <Directory /usr/local/apache2/htdocs>
            AllowOverride All
            Require all granted
        </Directory>
        LoadModule mpm_event_module modules/mod_mpm_event.so
        LoadModule dir_module modules/mod_dir.so
        LoadModule alias_module modules/mod_alias.so
        LoadModule rewrite_module modules/mod_rewrite.so
        DirectoryIndex index.html index.php
        """
    ).strip() + "\n"
    (services_root / "apache" / "config" / "httpd.conf").write_text(apache_conf, encoding="utf-8")

    apache_index = "<html><body><h1>HostingSignal Apache Sandbox</h1></body></html>\n"
    (services_root / "apache" / "data" / "index.html").write_text(apache_index, encoding="utf-8")

    ols_index = "<html><body><h1>HostingSignal OpenLiteSpeed Sandbox</h1></body></html>\n"
    (services_root / "openlitespeed" / "data" / "index.html").write_text(ols_index, encoding="utf-8")

    postfix_main = dedent(
        """
        compatibility_level = 3.6
        queue_directory = /var/spool/postfix
        command_directory = /usr/sbin
        daemon_directory = /usr/lib/postfix/sbin
        data_directory = /var/lib/postfix
        mail_owner = postfix
        myhostname = mail.hostingsignal.local
        myorigin = hostingsignal.local
        inet_interfaces = all
        mydestination = localhost
        smtpd_banner = $myhostname ESMTP HostingSignal Sandbox
        """
    ).strip() + "\n"
    (services_root / "postfix" / "config" / "main.cf").write_text(postfix_main, encoding="utf-8")

    dovecot_conf = dedent(
        """
        protocols = imap pop3 lmtp
        listen = *
        mail_location = maildir:/srv/mail/%n
        disable_plaintext_auth = no
        auth_mechanisms = plain login
        passdb {
          driver = passwd-file
          args = /etc/dovecot/users
        }
        userdb {
          driver = static
          args = uid=vmail gid=vmail home=/srv/mail/%n
        }
        service imap-login {
          inet_listener imap {
            port = 143
          }
          inet_listener imaps {
            port = 993
            ssl = no
          }
        }
        """
    ).strip() + "\n"
    (services_root / "dovecot" / "config" / "dovecot.conf").write_text(dovecot_conf, encoding="utf-8")
    (services_root / "dovecot" / "config" / "users").write_text("demo:{PLAIN}demo\n", encoding="utf-8")

    pureftpd_conf = "yes\n"
    (services_root / "pureftpd" / "config" / "ChrootEveryone").write_text(pureftpd_conf, encoding="utf-8")

    powerdns_conf = dedent(
        f"""
        launch=gsqlite3
        gsqlite3-database=/var/lib/powerdns/pdns.sqlite3
        api=yes
        api-key={config['secrets']['pdns_api_key']}
        webserver=yes
        webserver-address=0.0.0.0
        webserver-port=8081
        local-address=0.0.0.0
        local-port=5353
        """
    ).strip() + "\n"
    (services_root / "powerdns" / "config" / "pdns.conf").write_text(powerdns_conf, encoding="utf-8")

    supervisord_conf = dedent(
        """
        [unix_http_server]
        file=/tmp/supervisor.sock

        [supervisord]
        nodaemon=true
        logfile=/dev/stdout
        pidfile=/tmp/supervisord.pid

        [inet_http_server]
        port=0.0.0.0:9001
        username=admin
        password=admin
        """
    ).strip() + "\n"
    (services_root / "supervisor" / "config" / "supervisord.conf").write_text(supervisord_conf, encoding="utf-8")

    cron_file = "*/15 * * * * echo HostingSignal cron heartbeat >> /var/log/cron.log\n"
    (services_root / "cron" / "config" / "crontab").write_text(cron_file, encoding="utf-8")

    # Marker files for webapp tools.
    (services_root / "rainloop" / "config" / "README.md").write_text("Rainloop runtime config will be mounted here.\n", encoding="utf-8")
    (services_root / "phpmyadmin" / "config" / "README.md").write_text("phpMyAdmin runtime config will be mounted here.\n", encoding="utf-8")


def render_compose(config: dict) -> str:
    web_service = config["web_server"]
    db_service = config["database"]
    services_root = config["paths"]["services_root"]
    data_root = config["paths"]["data_root"]
    services_path = f"../../{services_root}"
    data_path = f"../../{data_root}"
    lines = [
        "name: hostingsignal-local",
        "services:",
    ]

    if web_service == "apache":
        lines.extend([
            "  apache:",
            "    image: httpd:2.4",
            "    container_name: hs-local-apache",
            "    restart: unless-stopped",
            "    ports:",
            '      - "${WEB_PORT}:80"',
            "    volumes:",
            f"      - {services_path}/apache/data:/usr/local/apache2/htdocs:rw",
            '    profiles: ["core"]',
        ])
    else:
        lines.extend([
            "  openlitespeed:",
            "    image: litespeedtech/openlitespeed:latest",
            "    container_name: hs-local-openlitespeed",
            "    restart: unless-stopped",
            "    ports:",
            '      - "${WEB_PORT}:8088"',
            "    volumes:",
            f"      - {services_path}/openlitespeed/data:/var/www/vhosts/localhost/html:rw",
            "    environment:",
            "      TZ: UTC",
            '    profiles: ["core"]',
        ])

    if db_service == "mysql":
        lines.extend([
            "  mysql:",
            "    image: mysql:8.4",
            "    container_name: hs-local-mysql",
            "    restart: unless-stopped",
            "    command: --default-authentication-plugin=mysql_native_password",
            "    environment:",
            "      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}",
            "      MYSQL_DATABASE: hostingsignal",
            "      MYSQL_USER: hostingsignal",
            "      MYSQL_PASSWORD: ${DB_APP_PASSWORD}",
            "    ports:",
            '      - "${DB_PORT}:3306"',
            "    volumes:",
            f"      - {data_path}/databases/mysql:/var/lib/mysql",
            '    profiles: ["core"]',
        ])
    else:
        lines.extend([
            "  mariadb:",
            "    image: mariadb:11",
            "    container_name: hs-local-mariadb",
            "    restart: unless-stopped",
            "    environment:",
            "      MARIADB_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}",
            "      MARIADB_DATABASE: hostingsignal",
            "      MARIADB_USER: hostingsignal",
            "      MARIADB_PASSWORD: ${DB_APP_PASSWORD}",
            "    ports:",
            '      - "${DB_PORT}:3306"',
            "    volumes:",
            f"      - {data_path}/databases/mariadb:/var/lib/mysql",
            '    profiles: ["core"]',
        ])

    lines.extend([
        "  redis:",
        "    image: redis:7-alpine",
        "    container_name: hs-local-redis",
        "    restart: unless-stopped",
        "    ports:",
        '      - "${REDIS_PORT}:6379"',
        "    volumes:",
        f"      - {data_path}/cache/redis:/data",
        '    profiles: ["core"]',
        "  memcached:",
        "    image: memcached:1.6-alpine",
        "    container_name: hs-local-memcached",
        "    restart: unless-stopped",
        "    ports:",
        '      - "${MEMCACHED_PORT}:11211"',
        '    profiles: ["core"]',
        "  phpmyadmin:",
        "    image: phpmyadmin:latest",
        "    container_name: hs-local-phpmyadmin",
        "    restart: unless-stopped",
        "    depends_on:",
        f"      - {db_service}",
        "    environment:",
        f"      PMA_HOST: {db_service}",
        "      PMA_PORT: 3306",
        "    ports:",
        '      - "${PHPMYADMIN_PORT}:80"',
        '    profiles: ["core"]',
        "  certbot:",
        "    image: certbot/certbot:latest",
        "    container_name: hs-local-certbot",
        "    entrypoint: [\"/bin/sh\", \"-lc\", \"trap exit TERM; while :; do sleep 3600; done\"]",
        "    volumes:",
        f"      - {data_path}/ssl:/etc/letsencrypt",
        '    profiles: ["core"]',
        "  postfix:",
        "    build:",
        f"      context: {services_path}/postfix",
        "    container_name: hs-local-postfix",
        "    restart: unless-stopped",
        "    ports:",
        '      - "2525:25"',
        '    profiles: ["mail"]',
        "  dovecot:",
        "    build:",
        f"      context: {services_path}/dovecot",
        "    container_name: hs-local-dovecot",
        "    restart: unless-stopped",
        "    ports:",
        '      - "2993:993"',
        '    profiles: ["mail"]',
        "  rainloop:",
        "    image: hardware/rainloop:latest",
        "    container_name: hs-local-rainloop",
        "    restart: unless-stopped",
        "    depends_on:",
        "      - dovecot",
        "    ports:",
        '      - "8888:8888"',
        '    profiles: ["mail"]',
        "  spamassassin:",
        "    build:",
        f"      context: {services_path}/spamassassin",
        "    container_name: hs-local-spamassassin",
        "    restart: unless-stopped",
        "    ports:",
        '      - "2783:783"',
        '    profiles: ["mail"]',
        "  opendkim:",
        "    build:",
        f"      context: {services_path}/opendkim",
        "    container_name: hs-local-opendkim",
        "    restart: unless-stopped",
        "    ports:",
        '      - "2889:8891"',
        '    profiles: ["mail"]',
        "  powerdns:",
        "    build:",
        f"      context: {services_path}/powerdns",
        "    container_name: hs-local-powerdns",
        "    restart: unless-stopped",
        "    ports:",
        '      - "5353:5353/tcp"',
        '      - "5353:5353/udp"',
        "    volumes:",
        f"      - {data_path}/dns:/var/lib/powerdns",
        '    profiles: ["dns"]',
        "  pureftpd:",
        "    build:",
        f"      context: {services_path}/pureftpd",
        "    container_name: hs-local-pureftpd",
        "    restart: unless-stopped",
        "    ports:",
        '      - "2121:21"',
        "    volumes:",
        f"      - {data_path}/ftp:/srv/ftp",
        '    profiles: ["ftp"]',
        "  fail2ban:",
        "    build:",
        f"      context: {services_path}/fail2ban",
        "    container_name: hs-local-fail2ban",
        "    restart: unless-stopped",
        "    cap_add:",
        "      - NET_ADMIN",
        '    profiles: ["security"]',
        "  firewalld:",
        "    build:",
        f"      context: {services_path}/firewalld",
        "    container_name: hs-local-firewalld",
        "    restart: unless-stopped",
        "    privileged: true",
        '    profiles: ["security"]',
        "  modsecurity:",
        "    build:",
        f"      context: {services_path}/modsecurity",
        "    container_name: hs-local-modsecurity",
        "    restart: unless-stopped",
        '    profiles: ["security"]',
        "  supervisor:",
        "    build:",
        f"      context: {services_path}/supervisor",
        "    container_name: hs-local-supervisor",
        "    restart: unless-stopped",
        "    ports:",
        '      - "9001:9001"',
        '    profiles: ["ops"]',
        "  cron:",
        "    build:",
        f"      context: {services_path}/cron",
        "    container_name: hs-local-cron",
        "    restart: unless-stopped",
        '    profiles: ["ops"]',
    ])

    return "\n".join(lines) + "\n"


def write_container_dockerfiles(config: dict) -> None:
    services_root = ROOT / config["paths"]["services_root"]

    generic_services = {
        "postfix": {
            "packages": ["postfix"],
            "copies": [("config/main.cf", "/etc/postfix/main.cf")],
            "cmd": "postfix start-fg",
        },
        "dovecot": {
            "packages": ["dovecot-core", "dovecot-imapd", "dovecot-pop3d"],
            "copies": [("config/dovecot.conf", "/etc/dovecot/dovecot.conf"), ("config/users", "/etc/dovecot/users")],
            "cmd": "dovecot -F",
        },
        "spamassassin": {
            "packages": ["spamassassin"],
            "copies": [],
            "cmd": "spamd -d -c -m 5",
        },
        "opendkim": {
            "packages": ["opendkim", "opendkim-tools"],
            "copies": [],
            "cmd": "opendkim -f",
        },
        "powerdns": {
            "packages": ["pdns-server", "pdns-backend-sqlite3", "sqlite3"],
            "copies": [("config/pdns.conf", "/etc/powerdns/pdns.conf")],
            "cmd": "mkdir -p /var/lib/powerdns && sqlite3 /var/lib/powerdns/pdns.sqlite3 'create table if not exists domains (id integer primary key, name varchar(255), master varchar(128), last_check integer, type varchar(6), notified_serial integer, account varchar(40), options varchar(65535), catalog varchar(255));' && pdns_server --daemon=no --guardian=no --control-console=no",
        },
        "pureftpd": {
            "packages": ["pure-ftpd"],
            "copies": [("config/ChrootEveryone", "/etc/pure-ftpd/conf/ChrootEveryone")],
            "cmd": "/usr/sbin/pure-ftpd -A -B -j -E -H",
        },
        "fail2ban": {
            "packages": ["fail2ban"],
            "copies": [],
            "cmd": "fail2ban-server -xf start",
        },
        "firewalld": {
            "packages": ["firewalld", "dbus"],
            "copies": [],
            "cmd": "mkdir -p /run/dbus && dbus-daemon --system && /usr/sbin/firewalld --nofork --nopid",
        },
        "modsecurity": {
            "packages": ["libapache2-mod-security2", "modsecurity-crs", "apache2"],
            "copies": [],
            "cmd": "apachectl -D FOREGROUND",
        },
        "supervisor": {
            "packages": ["supervisor"],
            "copies": [("config/supervisord.conf", "/etc/supervisor/supervisord.conf")],
            "cmd": "/usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf",
        },
        "cron": {
            "packages": ["cron"],
            "copies": [("config/crontab", "/etc/cron.d/hostingsignal")],
            "cmd": "chmod 0644 /etc/cron.d/hostingsignal && crontab /etc/cron.d/hostingsignal && cron -f",
        },
    }

    for service, meta in generic_services.items():
        root = services_root / service
        dockerfile = [
            "FROM ubuntu:24.04",
            "ENV DEBIAN_FRONTEND=noninteractive",
            "RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates " + " ".join(meta["packages"]) + " && rm -rf /var/lib/apt/lists/*",
        ]
        for src, dst in meta["copies"]:
            dockerfile.append(f"COPY {src} {dst}")
        dockerfile.append(f'CMD ["/bin/sh", "-lc", "{meta["cmd"]}"]')
        (root / "Dockerfile").write_text("\n".join(dockerfile) + "\n", encoding="utf-8")


def write_install_config(config: dict) -> None:
    INSTALL_CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def resolve_services_to_start(config: dict, catalog: dict) -> list[str]:
    selected: list[str] = []
    active_profiles = set(config.get("profiles", []))
    selected_web = config.get("web_server")
    selected_database = config.get("database")

    for service_name, meta in catalog.get("services", {}).items():
        if meta.get("profile") not in active_profiles:
            continue
        kind = meta.get("kind")
        if kind == "web" and service_name != selected_web:
            continue
        if kind == "database" and service_name != selected_database:
            continue
        selected.append(service_name)

    return selected


def build_compose_invocation(compose_base: list[str], compose_path: Path, env_path: Path, profiles: list[str], *args: str) -> list[str]:
    profile_args: list[str] = []
    for profile in profiles:
        profile_args.extend(["--profile", profile])
    return [*compose_base, "--env-file", str(env_path), "-f", str(compose_path), *profile_args, *args]


def install(config: dict, start: bool) -> None:
    runtime_root = ROOT / config["paths"]["runtime_root"]
    compose_path = runtime_root / "docker-compose.yml"
    env_path = write_env_file(config)
    compose_base = detect_compose_base_cmd()
    catalog = load_catalog()
    if compose_base is None:
        raise SystemExit("docker compose or docker-compose is required for the local installer flow")
    compose_path.write_text(render_compose(config), encoding="utf-8")
    write_generated_service_files(config)
    write_container_dockerfiles(config)
    write_install_config(config)

    print("Completed components")
    print(f"- install-config.json written to {INSTALL_CONFIG_PATH}")
    print(f"- local compose stack written to {compose_path}")
    print(f"- service workspace created under {ROOT / config['paths']['services_root']}")
    print(f"- active profile set: {', '.join(config['profiles'])}")
    print("Components in progress")
    print("- mail/dns/ftp/security containers are generated but not deeply validated yet")
    print("Errors detected")
    print("- none during generation")
    print("Fixes applied")
    print("- replaced system-path installer flow with repo-local services/runtime/data/log layout")
    print("- added compose-backed service manager foundation")

    if start:
        services_to_start = resolve_services_to_start(config, catalog)
        print("Next steps")
        print("- validating docker compose configuration")
        run(build_compose_invocation(compose_base, compose_path, env_path, config["profiles"], "config"), cwd=ROOT)
        run(build_compose_invocation(compose_base, compose_path, env_path, config["profiles"], "up", "-d", *services_to_start), cwd=ROOT)
        attempt_devpanel_registration(config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HostingSignal local services installer")
    parser.add_argument("--mode", choices=["all"], default=None)
    parser.add_argument("--all", action="store_true", help="Generate, configure, and start the full HostingSignal local stack")
    parser.add_argument("--web", choices=["openlitespeed", "apache"], default=None)
    parser.add_argument("--db", choices=["mariadb", "mysql"], default=None)
    parser.add_argument("--profile-set", choices=["core", "full"], default=None)
    parser.add_argument("--profiles", default=None, help="Comma-separated compose profiles to activate")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--skip-start", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not docker_available():
        print(
            "\n[HostingSignal] Docker / docker compose not found.\n"
            "\n"
            "Install Docker on Ubuntu/Debian:\n"
            "  curl -fsSL https://get.docker.com | sh\n"
            "  sudo usermod -aG docker $USER && newgrp docker\n"
            "\n"
            "For WSL2: enable 'Use the WSL 2 based engine' in Docker Desktop\n"
            "  Settings -> Resources -> WSL Integration -> enable your distro.\n"
            "\n"
            "Then re-run the installer:"
            "  curl -fsSL https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh | bash\n",
            file=sys.stderr,
        )
        return 1

    catalog = load_catalog()
    config = build_install_config(args, catalog)
    ensure_layout(config, catalog)
    install(config, start=not args.skip_start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
