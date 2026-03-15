from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
INSTALL_CONFIG = ROOT / "configs" / "install-config.json"
CATALOG_PATH = ROOT / "configs" / "service-catalog.json"


@dataclass
class CommandResult:
    ok: bool
    code: int
    stdout: str
    stderr: str


class LocalServiceManager:
    def __init__(self, root: Path | None = None):
        self.root = root or ROOT
        self.install_config = self._load_json(INSTALL_CONFIG)
        self.catalog = self._load_json(CATALOG_PATH)
        self.profiles = self.install_config.get("profiles", ["core"])
        self.compose_base_cmd = self._detect_compose_base_cmd()
        runtime_root = self.install_config.get("paths", {}).get("runtime_root", "runtime/local-stack")
        self.compose_file = self.root / runtime_root / "docker-compose.yml"
        self.env_file = self.root / runtime_root / ".env"

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _run(cmd: list[str], cwd: Path, env_file: Path | None = None) -> CommandResult:
        final_cmd = cmd[:]
        if env_file and env_file.exists() and "docker" in cmd[:2]:
            final_cmd = [cmd[0], cmd[1], "--env-file", str(env_file), *cmd[2:]]
        proc = subprocess.run(final_cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return CommandResult(
            ok=proc.returncode == 0,
            code=proc.returncode,
            stdout=(proc.stdout or "").strip(),
            stderr=(proc.stderr or "").strip(),
        )

    @staticmethod
    def _detect_compose_base_cmd() -> list[str]:
        docker_compose = subprocess.run(
            ["docker", "compose", "version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if docker_compose.returncode == 0:
            return ["docker", "compose"]

        legacy_compose = subprocess.run(
            ["docker-compose", "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if legacy_compose.returncode == 0:
            return ["docker-compose"]

        raise RuntimeError("docker compose or docker-compose is required")

    def _compose(self, *args: str) -> CommandResult:
        profile_args: list[str] = []
        for profile in self.profiles:
            profile_args.extend(["--profile", profile])
        cmd = [*self.compose_base_cmd, "-f", str(self.compose_file), *profile_args, *args]
        return self._run(cmd, cwd=self.root, env_file=self.env_file)

    def start_service(self, service: str | None = None) -> dict[str, Any]:
        args = ["up", "-d"]
        if service:
            args.append(service)
        else:
            web = self.install_config.get("web_server", "apache")
            database = self.install_config.get("database", "mariadb")
            args.extend([web, database, "redis", "memcached", "phpmyadmin", "certbot"])
        result = self._compose(*args)
        return self._payload(result, action="start", service=service)

    def stop_service(self, service: str | None = None) -> dict[str, Any]:
        args = ["stop"]
        if service:
            args.append(service)
        result = self._compose(*args)
        return self._payload(result, action="stop", service=service)

    def restart_service(self, service: str | None = None) -> dict[str, Any]:
        args = ["restart"]
        if service:
            args.append(service)
        result = self._compose(*args)
        return self._payload(result, action="restart", service=service)

    def check_status(self, service: str | None = None) -> dict[str, Any]:
        result = self._compose("ps", "--format", "json")
        payload = self._payload(result, action="status", service=service)
        if result.ok:
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            services: list[dict[str, Any]] = []
            for line in lines:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if service and item.get("Service") != service:
                    continue
                services.append(item)
            payload["services"] = services
        return payload

    def validate_config(self) -> dict[str, Any]:
        result = self._compose("config")
        return self._payload(result, action="validate")

    @staticmethod
    def _payload(result: CommandResult, action: str, service: str | None = None) -> dict[str, Any]:
        return {
            "success": result.ok,
            "action": action,
            "service": service,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.code,
        }


def _main() -> int:
    parser = argparse.ArgumentParser(description="HostingSignal local service manager")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "validate"])
    parser.add_argument("service", nargs="?", default=None)
    args = parser.parse_args()

    try:
        manager = LocalServiceManager()
    except RuntimeError as exc:
        print(json.dumps({"success": False, "detail": str(exc)}, indent=2))
        return 1
    if args.command == "start":
        payload = manager.start_service(args.service)
    elif args.command == "stop":
        payload = manager.stop_service(args.service)
    elif args.command == "restart":
        payload = manager.restart_service(args.service)
    elif args.command == "status":
        payload = manager.check_status(args.service)
    else:
        payload = manager.validate_config()

    print(json.dumps(payload, indent=2))
    return 0 if payload.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(_main())
