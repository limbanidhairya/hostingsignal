#!/usr/bin/env python3
"""HS-Panel recovery manager.

Monitors configured services and attempts bounded auto-recovery.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT_DIR / "core" / "orchestrator" / "services.json"
LOG_DIR = ROOT_DIR / "logs" / "recovery"
STATE_FILE = LOG_DIR / "state.json"
EVENT_LOG = LOG_DIR / "events.jsonl"

MAX_RESTARTS = 3
HEALTH_INTERVAL_SECONDS = 30


@dataclass
class ServiceState:
    consecutive_failures: int = 0
    restart_attempts: int = 0
    unhealthy: bool = False
    last_failure_at: str = ""
    last_recovery_at: str = ""


@dataclass
class ServiceCheckResult:
    service: str
    active: bool
    status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(args, capture_output=True, text=True, check=False, timeout=25)
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def load_registry_services() -> list[str]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    services: list[str] = []
    for group in data.get("startup_order", []):
        for service in data.get(group, []):
            name = str(service)
            if name not in services:
                services.append(name)
    return services


def load_state() -> dict[str, ServiceState]:
    if not STATE_FILE.exists():
        return {}
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    state: dict[str, ServiceState] = {}
    for key, value in (raw or {}).items():
        if not isinstance(value, dict):
            continue
        state[key] = ServiceState(
            consecutive_failures=int(value.get("consecutive_failures", 0)),
            restart_attempts=int(value.get("restart_attempts", 0)),
            unhealthy=bool(value.get("unhealthy", False)),
            last_failure_at=str(value.get("last_failure_at", "")),
            last_recovery_at=str(value.get("last_recovery_at", "")),
        )
    return state


def save_state(state: dict[str, ServiceState]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        name: {
            "consecutive_failures": item.consecutive_failures,
            "restart_attempts": item.restart_attempts,
            "unhealthy": item.unhealthy,
            "last_failure_at": item.last_failure_at,
            "last_recovery_at": item.last_recovery_at,
        }
        for name, item in state.items()
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_event(event: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def check_service(service: str) -> ServiceCheckResult:
    code, out, _err = run_cmd(["systemctl", "is-active", service])
    status = out if out else "inactive"
    return ServiceCheckResult(service=service, active=code == 0 and status == "active", status=status)


def restart_service(service: str) -> bool:
    code, _out, _err = run_cmd(["systemctl", "restart", service])
    if code != 0:
        return False
    # Small delay before status probe.
    time.sleep(1)
    return check_service(service).active


def evaluate_once(verbose: bool = False) -> dict:
    services = load_registry_services()
    state = load_state()
    checks = []

    for service in services:
        prev = state.get(service, ServiceState())
        result = check_service(service)

        if result.active:
            if prev.consecutive_failures > 0 or prev.unhealthy:
                prev.last_recovery_at = utc_now()
                append_event(
                    {
                        "ts": utc_now(),
                        "type": "service_recovered",
                        "service": service,
                        "status": result.status,
                    }
                )
            prev.consecutive_failures = 0
            prev.restart_attempts = 0
            prev.unhealthy = False
        else:
            prev.consecutive_failures += 1
            prev.last_failure_at = utc_now()

            if prev.restart_attempts < MAX_RESTARTS:
                prev.restart_attempts += 1
                restarted = restart_service(service)
                append_event(
                    {
                        "ts": utc_now(),
                        "type": "restart_attempt",
                        "service": service,
                        "attempt": prev.restart_attempts,
                        "result": "success" if restarted else "failed",
                        "status_before": result.status,
                    }
                )
                if restarted:
                    prev.consecutive_failures = 0
                    prev.unhealthy = False
                    prev.last_recovery_at = utc_now()
                else:
                    prev.unhealthy = prev.restart_attempts >= MAX_RESTARTS
            else:
                prev.unhealthy = True
                append_event(
                    {
                        "ts": utc_now(),
                        "type": "service_unhealthy",
                        "service": service,
                        "status": result.status,
                    }
                )

        state[service] = prev
        checks.append(
            {
                "service": service,
                "status": result.status,
                "active": result.active,
                "restart_attempts": prev.restart_attempts,
                "unhealthy": prev.unhealthy,
            }
        )

    save_state(state)

    summary = {
        "ts": utc_now(),
        "services": checks,
        "unhealthy_count": len([x for x in checks if x["unhealthy"]]),
    }
    if verbose:
        print(json.dumps(summary, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HS-Panel recovery manager")
    parser.add_argument("--once", action="store_true", help="Run one health-check cycle and exit")
    parser.add_argument("--verbose", action="store_true", help="Print JSON summary output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.once:
        evaluate_once(verbose=args.verbose)
        return 0

    while True:
        evaluate_once(verbose=args.verbose)
        time.sleep(HEALTH_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
