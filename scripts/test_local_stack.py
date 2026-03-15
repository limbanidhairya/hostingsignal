from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_CONFIG = ROOT / "configs" / "install-config.json"


def load_install_config() -> dict:
    if not INSTALL_CONFIG.exists():
        raise SystemExit("install-config.json not found. Run ./install.sh first.")
    return json.loads(INSTALL_CONFIG.read_text(encoding="utf-8"))


def check_tcp(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (True, f"tcp://{host}:{port} reachable")
    except OSError as exc:
        return (False, f"tcp://{host}:{port} failed: {exc}")


def check_http(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return (True, f"{url} -> HTTP {response.status}")
    except Exception as exc:
        return (False, f"{url} failed: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the local HostingSignal stack")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    config = load_install_config()
    web_port = int(config["ports"]["web"])
    db_port = int(config["ports"]["database"])
    redis_port = int(config["ports"]["redis"])
    memcached_port = int(config["ports"]["memcached"])
    phpmyadmin_port = int(config["ports"]["phpmyadmin"])

    checks = [
        check_http(f"http://{args.host}:{web_port}"),
        check_tcp(args.host, db_port),
        check_tcp(args.host, redis_port),
        check_tcp(args.host, memcached_port),
        check_http(f"http://{args.host}:{phpmyadmin_port}"),
    ]

    failures = 0
    for ok, message in checks:
        marker = "PASS" if ok else "FAIL"
        print(f"[{marker}] {message}")
        if not ok:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
