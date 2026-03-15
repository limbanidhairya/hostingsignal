#!/usr/bin/env python3
"""Container runtime manager for HS-Panel.

Supports Docker/Podman detection and common lifecycle operations.
"""
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class RuntimeResult:
    ok: bool
    code: int
    stdout: str
    stderr: str


class ContainerRunner:
    def __init__(self, preferred_runtime: str | None = None):
        self.runtime = self._detect_runtime(preferred_runtime)

    @staticmethod
    def _detect_runtime(preferred: str | None = None) -> str | None:
        if preferred:
            return preferred if shutil.which(preferred) else None
        if shutil.which("docker"):
            return "docker"
        if shutil.which("podman"):
            return "podman"
        return None

    def available(self) -> dict[str, Any]:
        if not self.runtime:
            return {"available": False, "runtime": None, "detail": "No docker/podman runtime found"}

        probe = self._run([self.runtime, "info"])
        detail = self._with_runtime_hint(probe.stderr or probe.stdout or "runtime unavailable")
        return {
            "available": probe.ok,
            "runtime": self.runtime,
            "detail": "ready" if probe.ok else detail,
        }

    @staticmethod
    def _with_runtime_hint(detail: str) -> str:
        message = (detail or "").strip()
        lowered = message.lower()
        if "permission denied" in lowered and "docker.sock" in lowered:
            return (
                message
                + " | hint: run with sudo or add runtime user to docker group "
                + "(sudo usermod -aG docker $USER) then re-login"
            )
        return message

    @staticmethod
    def _run(cmd: list[str], timeout: int = 30) -> RuntimeResult:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return RuntimeResult(
                ok=proc.returncode == 0,
                code=proc.returncode,
                stdout=(proc.stdout or "").strip(),
                stderr=(proc.stderr or "").strip(),
            )
        except Exception as exc:
            return RuntimeResult(ok=False, code=1, stdout="", stderr=str(exc))

    def _require_runtime(self) -> str:
        if not self.runtime:
            raise RuntimeError("No supported container runtime installed (docker/podman)")
        return self.runtime

    def list_containers(self, include_all: bool = True) -> dict[str, Any]:
        runtime = self._require_runtime()
        args = [runtime, "ps"]
        if include_all:
            args.append("-a")
        args += ["--format", "{{json .}}"]
        result = self._run(args)
        if not result.ok:
            return {"success": False, "detail": self._with_runtime_hint(result.stderr or result.stdout)}

        containers = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        return {"success": True, "runtime": runtime, "count": len(containers), "containers": containers}

    def start(self, name: str) -> dict[str, Any]:
        runtime = self._require_runtime()
        result = self._run([runtime, "start", name])
        return {
            "success": result.ok,
            "runtime": runtime,
            "name": name,
            "detail": self._with_runtime_hint(result.stderr or result.stdout),
        }

    def stop(self, name: str, timeout_seconds: int = 10) -> dict[str, Any]:
        runtime = self._require_runtime()
        result = self._run([runtime, "stop", "-t", str(timeout_seconds), name], timeout=timeout_seconds + 15)
        return {
            "success": result.ok,
            "runtime": runtime,
            "name": name,
            "detail": self._with_runtime_hint(result.stderr or result.stdout),
        }

    def remove(self, name: str, force: bool = False) -> dict[str, Any]:
        runtime = self._require_runtime()
        cmd = [runtime, "rm"]
        if force:
            cmd.append("-f")
        cmd.append(name)
        result = self._run(cmd)
        return {
            "success": result.ok,
            "runtime": runtime,
            "name": name,
            "detail": self._with_runtime_hint(result.stderr or result.stdout),
        }

    def logs(self, name: str, tail: int = 100) -> dict[str, Any]:
        runtime = self._require_runtime()
        result = self._run([runtime, "logs", "--tail", str(tail), name], timeout=45)
        return {
            "success": result.ok,
            "runtime": runtime,
            "name": name,
            "logs": result.stdout,
            "detail": self._with_runtime_hint(result.stderr),
        }

    def run(
        self,
        image: str,
        name: str | None = None,
        detach: bool = True,
        ports: list[str] | None = None,
        env_vars: list[str] | None = None,
        command: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._require_runtime()
        cmd = [runtime, "run"]
        if detach:
            cmd.append("-d")
        if name:
            cmd += ["--name", name]
        for p in ports or []:
            cmd += ["-p", p]
        for env_var in env_vars or []:
            cmd += ["-e", env_var]
        cmd.append(image)
        if command:
            cmd += shlex.split(command)

        result = self._run(cmd, timeout=90)
        return {
            "success": result.ok,
            "runtime": runtime,
            "image": image,
            "name": name,
            "container_id": result.stdout if result.ok else "",
            "detail": self._with_runtime_hint(result.stderr or result.stdout),
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HS-Panel container runner")
    parser.add_argument("--runtime", default=None, help="Force runtime: docker|podman")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--running-only", action="store_true")

    start_cmd = sub.add_parser("start")
    start_cmd.add_argument("name")

    stop_cmd = sub.add_parser("stop")
    stop_cmd.add_argument("name")
    stop_cmd.add_argument("--timeout", type=int, default=10)

    rm_cmd = sub.add_parser("remove")
    rm_cmd.add_argument("name")
    rm_cmd.add_argument("--force", action="store_true")

    logs_cmd = sub.add_parser("logs")
    logs_cmd.add_argument("name")
    logs_cmd.add_argument("--tail", type=int, default=100)

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("image")
    run_cmd.add_argument("--name", default=None)
    run_cmd.add_argument("--attach", action="store_true")
    run_cmd.add_argument("--port", action="append", default=[])
    run_cmd.add_argument("--env", action="append", default=[])
    run_cmd.add_argument("--run-command", default=None)

    return parser


def main() -> int:
    args = _build_parser().parse_args()
    runner = ContainerRunner(preferred_runtime=args.runtime)

    try:
        if args.command == "status":
            payload = runner.available()
        elif args.command == "list":
            payload = runner.list_containers(include_all=not args.running_only)
        elif args.command == "start":
            payload = runner.start(args.name)
        elif args.command == "stop":
            payload = runner.stop(args.name, timeout_seconds=args.timeout)
        elif args.command == "remove":
            payload = runner.remove(args.name, force=args.force)
        elif args.command == "logs":
            payload = runner.logs(args.name, tail=args.tail)
        elif args.command == "run":
            payload = runner.run(
                image=args.image,
                name=args.name,
                detach=not args.attach,
                ports=args.port,
                env_vars=args.env,
                command=args.run_command,
            )
        else:
            payload = {"success": False, "detail": f"unsupported command: {args.command}"}
    except RuntimeError as exc:
        payload = {"success": False, "detail": str(exc), "available": False}

    print(json.dumps(payload, indent=2))
    return 0 if payload.get("success", payload.get("available", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
