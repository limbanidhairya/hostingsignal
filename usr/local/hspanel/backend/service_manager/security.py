"""
service_manager/security.py — Firewall and WAF security manager
Controls CSF and ModSecurity operations used by HS-Panel.
"""
from __future__ import annotations

import ipaddress
import logging
from pathlib import Path

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

CSF_BIN = "/usr/sbin/csf"
MODSEC_MAIN_CONF = "/etc/modsecurity/modsecurity.conf"
MODSEC_RULES_DIR = "/etc/modsecurity"


class SecurityManager(BaseServiceManager):
    """Manage CSF firewall and ModSecurity WAF."""

    # ------------------------------------------------------------------
    # CSF firewall operations
    # ------------------------------------------------------------------
    def reload(self) -> ServiceResult:
        rc, out, err = self._sysop("reload_csf")
        if rc == 0:
            return ServiceResult(True, out or "CSF reloaded")

        # Fallback to direct CLI when wrap_sysop is not yet expanded.
        rc, out, err = self._run([CSF_BIN, "-r"], timeout=30)
        return ServiceResult(rc == 0, out or err or "CSF reload completed")

    def status(self) -> dict:
        fw = self.service_status("csf")
        lfd = self.service_status("lfd")
        return {"csf": fw, "lfd": lfd}

    def enable_csf(self) -> ServiceResult:
        conf = Path("/etc/csf/csf.conf")
        if not conf.exists():
            return ServiceResult(False, "CSF config not found")

        content = conf.read_text()
        if 'TESTING = "1"' in content:
            content = content.replace('TESTING = "1"', 'TESTING = "0"')
            conf.write_text(content)

        enable_res = self.enable_service("csf")
        restart_res = self.restart_service("csf")
        if enable_res.success and restart_res.success:
            return ServiceResult(True, "CSF enabled and started")
        return ServiceResult(False, f"Enable/restart failed: {enable_res.message} | {restart_res.message}")

    def disable_csf(self) -> ServiceResult:
        stop = self.stop_service("csf")
        dis = self.systemctl("disable", "csf")
        if stop.success and dis.success:
            return ServiceResult(True, "CSF stopped and disabled")
        return ServiceResult(False, f"Disable failed: {stop.message} | {dis.message}")

    def allow_ip(self, ip: str, comment: str = "HS-Panel allow") -> ServiceResult:
        if not self._validate_ip(ip):
            return ServiceResult(False, f"Invalid IP: {ip}")
        rc, out, err = self._run([CSF_BIN, "-a", ip, comment], timeout=15)
        return ServiceResult(rc == 0, out or err or f"Allowed IP: {ip}")

    def deny_ip(self, ip: str, comment: str = "HS-Panel deny") -> ServiceResult:
        if not self._validate_ip(ip):
            return ServiceResult(False, f"Invalid IP: {ip}")
        rc, out, err = self._run([CSF_BIN, "-d", ip, comment], timeout=15)
        return ServiceResult(rc == 0, out or err or f"Denied IP: {ip}")

    def remove_ip(self, ip: str) -> ServiceResult:
        if not self._validate_ip(ip):
            return ServiceResult(False, f"Invalid IP: {ip}")
        rc, out, err = self._run([CSF_BIN, "-dr", ip], timeout=15)
        return ServiceResult(rc == 0, out or err or f"Removed deny rule for IP: {ip}")

    # ------------------------------------------------------------------
    # ModSecurity operations
    # ------------------------------------------------------------------
    def modsec_status(self) -> ServiceResult:
        conf = Path(MODSEC_MAIN_CONF)
        if not conf.exists():
            return ServiceResult(False, "ModSecurity config not found")

        mode = "unknown"
        for line in conf.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("SecRuleEngine"):
                mode = stripped.split(maxsplit=1)[1] if len(stripped.split()) > 1 else "unknown"
                break
        return ServiceResult(True, "ModSecurity status", {"mode": mode})

    def set_modsec_mode(self, mode: str) -> ServiceResult:
        mode = mode.strip()
        if mode not in {"On", "Off", "DetectionOnly"}:
            return ServiceResult(False, f"Invalid ModSecurity mode: {mode}")

        conf = Path(MODSEC_MAIN_CONF)
        if not conf.exists():
            return ServiceResult(False, "ModSecurity config not found")

        lines = conf.read_text().splitlines()
        updated = []
        replaced = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("SecRuleEngine"):
                updated.append(f"SecRuleEngine {mode}")
                replaced = True
            else:
                updated.append(line)

        if not replaced:
            updated.append(f"SecRuleEngine {mode}")

        conf.write_text("\n".join(updated) + "\n")
        return self.reload()

    def disable_rule(self, rule_id: str) -> ServiceResult:
        if not rule_id.isdigit():
            return ServiceResult(False, f"Invalid rule id: {rule_id}")

        custom_rules = Path(MODSEC_RULES_DIR) / "modsecurity_hspanel_exclusions.conf"
        custom_rules.parent.mkdir(parents=True, exist_ok=True)
        line = f"SecRuleRemoveById {rule_id}"

        existing = custom_rules.read_text().splitlines() if custom_rules.exists() else []
        if line not in existing:
            existing.append(line)
            custom_rules.write_text("\n".join(existing) + "\n")

        return self.reload()

    def enable_rule(self, rule_id: str) -> ServiceResult:
        if not rule_id.isdigit():
            return ServiceResult(False, f"Invalid rule id: {rule_id}")

        custom_rules = Path(MODSEC_RULES_DIR) / "modsecurity_hspanel_exclusions.conf"
        if not custom_rules.exists():
            return ServiceResult(True, "Rule already enabled")

        line = f"SecRuleRemoveById {rule_id}"
        lines = [l for l in custom_rules.read_text().splitlines() if l.strip() != line]
        custom_rules.write_text("\n".join(lines) + ("\n" if lines else ""))

        return self.reload()

    @staticmethod
    def _validate_ip(ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
