"""HS-Panel service orchestrator.

Dependency-aware orchestration wrapper around systemctl for WSL/Linux runtime.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path(__file__).with_name("services.json")


@dataclass
class CommandResult:
    ok: bool
    code: int
    stdout: str
    stderr: str


class ServiceOrchestrator:
    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or REGISTRY_PATH
        self.registry = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        with self.registry_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Invalid services registry format")
        return data

    def _run_systemctl(self, action: str, service: str) -> CommandResult:
        proc = subprocess.run(
            ["systemctl", action, service],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        return CommandResult(
            ok=proc.returncode == 0,
            code=proc.returncode,
            stdout=(proc.stdout or "").strip(),
            stderr=(proc.stderr or "").strip(),
        )

    def _expand_target(self, target: str) -> list[str]:
        normalized = (target or "").strip().lower()
        if not normalized:
            return []

        aliases = self.registry.get("aliases", {})
        if normalized in aliases:
            items = aliases.get(normalized, [])
            return [str(x) for x in items]

        for group in self.registry.get("startup_order", []):
            if normalized == str(group).lower():
                services = self.registry.get(group, [])
                return [str(x) for x in services]

        return [target]

    def _all_services(self) -> list[str]:
        services: list[str] = []
        for group in self.registry.get("startup_order", []):
            for svc in self.registry.get(group, []):
                svc_name = str(svc)
                if svc_name not in services:
                    services.append(svc_name)
        return services

    def service_status(self, target: str | None = None) -> dict[str, Any]:
        services = self._all_services() if not target else self._expand_target(target)
        if not services:
            return {"success": False, "detail": "No matching services"}

        output = []
        for service in services:
            result = self._run_systemctl("is-active", service)
            state = result.stdout if result.ok else (result.stdout or "inactive")
            output.append(
                {
                    "service": service,
                    "status": state or "unknown",
                    "ok": result.ok,
                }
            )
        return {"success": True, "services": output}

    def service_action(self, action: str, target: str) -> dict[str, Any]:
        if action not in {"start", "stop", "restart", "reload"}:
            return {"success": False, "detail": f"Unsupported action: {action}"}

        services = self._expand_target(target)
        if not services:
            return {"success": False, "detail": f"Unknown target: {target}"}

        results = []
        for service in services:
            result = self._run_systemctl(action, service)
            results.append(
                {
                    "service": service,
                    "action": action,
                    "ok": result.ok,
                    "code": result.code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )

        return {
            "success": all(x["ok"] for x in results),
            "target": target,
            "action": action,
            "results": results,
        }

    def ordered_start(self) -> dict[str, Any]:
        results = []
        for group in self.registry.get("startup_order", []):
            services = [str(x) for x in self.registry.get(group, [])]
            for service in services:
                result = self._run_systemctl("start", service)
                results.append(
                    {
                        "group": str(group),
                        "service": service,
                        "ok": result.ok,
                        "code": result.code,
                        "stderr": result.stderr,
                    }
                )
        return {"success": all(x["ok"] for x in results), "results": results}
