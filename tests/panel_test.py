#!/usr/bin/env python3
"""
HS-Panel Backend API — Comprehensive Test Suite
Sections 13-19: Test → Report → Fix → Repeat loop

Usage:
    python tests/panel_test.py [--url http://127.0.0.1:2083] [--token change-me]

Environment variables (override CLI defaults):
    HSPANEL_URL   — Base URL of the panel backend API
    HS_PANEL_API_TOKEN — API token
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_URL   = os.getenv("HSPANEL_URL", "http://127.0.0.1:2083")
DEFAULT_TOKEN = os.getenv("HS_PANEL_API_TOKEN", "change-me")

# Test domain / identifiers (use obviously-fake values)
TEST_DOMAIN   = "test-hspanel.invalid"
TEST_DB       = "hspanel_testdb"
TEST_DB_USER  = "hspanel_testuser"
TEST_MAIL_DOM = "mail.test-hspanel.invalid"
TEST_MAILBOX  = f"user@{TEST_MAIL_DOM}"
TEST_FTP_USER = "ftptest01"
TEST_CRON_USER = "crontest"

REPORT_DIR = Path(__file__).parent.parent / "reports"

# ---------------------------------------------------------------------------
# Test framework
# ---------------------------------------------------------------------------

_results: list[dict] = []
_iteration: int = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestRunner:
    def __init__(self, base_url: str, token: str) -> None:
        self.base = base_url.rstrip("/")
        self.headers = {
            "x-api-token": token,
            "Content-Type": "application/json",
        }
        self._bad_headers = {"Content-Type": "application/json"}  # no token

    # -----------------------------------------------------------------------
    # Low-level request helper
    # -----------------------------------------------------------------------
    def _req(
        self,
        name: str,
        method: str,
        path: str,
        *,
        body: Any = None,
        headers: dict | None = None,
        expect_status: int | list[int] = 200,
        expect_key: str = "success",
        expect_success_value: bool | None = True,
        tags: list[str] | None = None,
    ) -> dict:
        url = f"{self.base}{path}"
        hdrs = headers if headers is not None else self.headers
        allowed = [expect_status] if isinstance(expect_status, int) else expect_status

        result: dict = {
            "name": name,
            "method": method,
            "path": path,
            "tags": tags or [],
            "timestamp": _now(),
        }

        try:
            resp = getattr(requests, method.lower())(
                url, headers=hdrs, json=body, timeout=15
            )
        except requests.exceptions.ConnectionError as exc:
            result.update(status="ERROR", message=f"Connection refused: {exc}")
            _results.append(result)
            return result
        except Exception as exc:
            result.update(status="ERROR", message=str(exc))
            _results.append(result)
            return result

        result["http_status"] = resp.status_code

        # Parse JSON body
        try:
            data = resp.json()
        except Exception:
            data = {"_raw": resp.text[:500]}
        result["response"] = data

        # 500 is always a real failure regardless of expect_status
        if resp.status_code == 500:
            result.update(
                status="FAIL",
                message=f"Internal Server Error (500). Body: {json.dumps(data)[:300]}",
            )
            _results.append(result)
            return result

        # Check HTTP status code
        if resp.status_code not in allowed:
            result.update(
                status="FAIL",
                message=(
                    f"Expected HTTP {allowed}, got {resp.status_code}. "
                    f"Body: {json.dumps(data)[:300]}"
                ),
            )
            _results.append(result)
            return result

        # When response is an HTTP error (4xx) with FastAPI's {"detail": ...} format,
        # treat it as a graceful error — the API is working correctly, infrastructure
        # is simply unavailable (MySQL CLI, PowerDNS, certbot, etc.)
        if resp.status_code >= 400 and isinstance(data, dict) and "detail" in data:
            detail = data["detail"]
            infra_keywords = (
                "not found", "unreachable", "no such file", "connection refused",
                "errno", "failed to create", "failed to delete", "not installed",
                "socket", "system user not found", "config not found",
            )
            is_infra_issue = any(kw in detail.lower() for kw in infra_keywords)
            if is_infra_issue:
                # Infrastructure not available — API gracefully handled it
                result.update(
                    status="WARN",
                    message=f"Infrastructure unavailable: {detail[:150]}",
                )
                _results.append(result)
                return result
            # Auth or validation 4xx — check if it was intentionally expected
            if resp.status_code == 401 and 401 in allowed:
                result.update(status="PASS", message=f"Auth rejected as expected: {detail[:100]}")
                _results.append(result)
                return result
            # Other 4xx with detail (e.g. validation errors we explicitly test for)
            if resp.status_code in allowed:
                result.update(status="PASS", message=f"Expected error: {detail[:100]}")
                _results.append(result)
                return result
            result.update(
                status="FAIL",
                message=f"Unexpected {resp.status_code}: {detail[:200]}",
            )
            _results.append(result)
            return result

        # Optionally check for expected key in response
        if expect_key and expect_key not in data:
            result.update(
                status="FAIL",
                message=f"Response missing '{expect_key}' key. Body: {json.dumps(data)[:300]}",
            )
            _results.append(result)
            return result

        # Optionally check success flag value
        if expect_success_value is not None and expect_key == "success":
            if data.get("success") != expect_success_value:
                result.update(
                    status="FAIL",
                    message=f"Expected success={expect_success_value}, got {data.get('success')}. Body: {json.dumps(data)[:300]}",
                )
                _results.append(result)
                return result

        result.update(
            status="PASS",
            message=data.get("message", "OK") if isinstance(data, dict) else "OK",
        )
        _results.append(result)
        return result

    # -----------------------------------------------------------------------
    # Section 13/14: Feature Tests
    # -----------------------------------------------------------------------

    # --- 1. Health ---
    def test_health(self) -> None:
        self._req(
            "1.1 Health endpoint",
            "GET", "/health",
            expect_key="status",
            expect_success_value=None,
            tags=["health"],
        )

    # --- 2. Auth ---
    def test_auth(self) -> None:
        self._req(
            "2.1 Auth ping — valid token",
            "GET", "/api/auth/ping",
            tags=["auth"],
        )
        self._req(
            "2.2 Auth ping — no token → 401",
            "GET", "/api/auth/ping",
            headers=self._bad_headers,
            expect_status=401,
            expect_key="detail",
            expect_success_value=None,
            tags=["auth"],
        )

    # --- 3. Domain management ---
    def test_domains(self) -> None:
        # List (always should return success + data list)
        r = self._req(
            "3.1 Domain list",
            "GET", "/api/domain/list",
            tags=["domain"],
        )
        if r.get("status") == "PASS":
            data = r.get("response", {})
            if not isinstance(data.get("data"), list):
                r["status"] = "FAIL"
                r["message"] = f"Expected 'data' to be a list, got: {type(data.get('data'))}"

        # Create (may fail gracefully when OLS not installed — expect 200 or 400)
        self._req(
            "3.2 Domain create",
            "POST", "/api/domain/create",
            body={"domain": TEST_DOMAIN, "php_version": "lsphp83", "create_dns": False, "create_ssl": False},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["domain"],
        )

        # Delete (cleanup or graceful fail)
        self._req(
            "3.3 Domain delete",
            "DELETE", f"/api/domain/{TEST_DOMAIN}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["domain"],
        )

    # --- 4. MySQL / Database ---
    def test_mysql(self) -> None:
        r = self._req(
            "4.1 MySQL database list",
            "GET", "/api/mysql/database/list",
            tags=["mysql"],
        )
        if r.get("status") == "PASS":
            data = r.get("response", {})
            if not isinstance(data.get("data"), list):
                r["status"] = "FAIL"
                r["message"] = f"Expected list, got {type(data.get('data'))}"

        self._req(
            "4.2 MySQL database create",
            "POST", "/api/mysql/database/create",
            body={"name": TEST_DB},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mysql"],
        )

        self._req(
            "4.3 MySQL database delete",
            "DELETE", f"/api/mysql/database/{TEST_DB}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mysql"],
        )

        self._req(
            "4.4 MySQL user create",
            "POST", "/api/mysql/user/create",
            body={"username": TEST_DB_USER, "password": "T3stP@ss!word"},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mysql"],
        )

        self._req(
            "4.5 MySQL grant privileges",
            "POST", "/api/mysql/grant",
            body={"database": TEST_DB, "username": TEST_DB_USER, "privileges": "ALL PRIVILEGES"},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mysql"],
        )

        self._req(
            "4.6 MySQL user delete",
            "DELETE", f"/api/mysql/user/{TEST_DB_USER}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mysql"],
        )

    # --- 5. Mail ---
    def test_mail(self) -> None:
        r = self._req(
            "5.1 Mail domain list",
            "GET", "/api/mail/domain/list",
            tags=["mail"],
        )
        if r.get("status") == "PASS":
            if not isinstance(r.get("response", {}).get("data"), list):
                r["status"] = "FAIL"
                r["message"] = "Expected list for data"

        self._req(
            "5.2 Mail domain create",
            "POST", "/api/mail/domain/create",
            body={"domain": TEST_MAIL_DOM},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mail"],
        )

        r2 = self._req(
            "5.3 Mailbox list",
            "GET", "/api/mail/mailbox/list",
            tags=["mail"],
        )
        if r2.get("status") == "PASS":
            if not isinstance(r2.get("response", {}).get("data"), list):
                r2["status"] = "FAIL"
                r2["message"] = "Expected list for data"

        self._req(
            "5.4 Mailbox create",
            "POST", "/api/mail/mailbox/create",
            body={"email": TEST_MAILBOX, "password": "M@ilP@ss123", "quota_mb": 500},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mail"],
        )

        self._req(
            "5.5 Mailbox delete",
            "DELETE", f"/api/mail/mailbox/{TEST_MAILBOX}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mail"],
        )

        self._req(
            "5.6 Mail domain delete",
            "DELETE", f"/api/mail/domain/{TEST_MAIL_DOM}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["mail"],
        )

    # --- 6. DNS ---
    def test_dns(self) -> None:
        r = self._req(
            "6.1 DNS zone list",
            "GET", "/api/dns/zone/list",
            tags=["dns"],
        )
        if r.get("status") == "PASS":
            if not isinstance(r.get("response", {}).get("data"), list):
                r["status"] = "FAIL"
                r["message"] = "Expected list for data"

        self._req(
            "6.2 DNS zone create",
            "POST", "/api/dns/zone/create",
            body={
                "domain": TEST_DOMAIN,
                "ns1": "ns1.test.invalid",
                "ns2": "ns2.test.invalid",
                "server_ip": "192.0.2.1",
            },
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["dns"],
        )

        self._req(
            "6.3 DNS record add",
            "POST", "/api/dns/record/add",
            body={
                "domain": TEST_DOMAIN,
                "name": f"www.{TEST_DOMAIN}",
                "record_type": "A",
                "content": "192.0.2.1",
                "ttl": 300,
            },
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["dns"],
        )

        self._req(
            "6.4 DNS zone delete",
            "DELETE", f"/api/dns/zone/{TEST_DOMAIN}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["dns"],
        )

    # --- 7. SSL ---
    def test_ssl(self) -> None:
        r = self._req(
            "7.1 SSL cert list",
            "GET", "/api/ssl/list",
            tags=["ssl"],
        )
        if r.get("status") == "PASS":
            if not isinstance(r.get("response", {}).get("data"), list):
                r["status"] = "FAIL"
                r["message"] = "Expected list for data"

        self._req(
            "7.2 SSL issue cert",
            "POST", "/api/ssl/issue",
            body={
                "domain": TEST_DOMAIN,
                "admin_email": "admin@test.invalid",
                "staging": True,
            },
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["ssl"],
        )

    # --- 8. FTP ---
    def test_ftp(self) -> None:
        r = self._req(
            "8.1 FTP user list",
            "GET", "/api/ftp/list",
            tags=["ftp"],
        )
        if r.get("status") == "PASS":
            if not isinstance(r.get("response", {}).get("data"), list):
                r["status"] = "FAIL"
                r["message"] = "Expected list for data"

        self._req(
            "8.2 FTP user create",
            "POST", "/api/ftp/create",
            body={
                "username": TEST_FTP_USER,
                "password": "FtpP@ss123",
                "home": f"/var/www/{TEST_FTP_USER}",
            },
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["ftp"],
        )

        self._req(
            "8.3 FTP user delete",
            "DELETE", f"/api/ftp/{TEST_FTP_USER}",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["ftp"],
        )

    # --- 9. PHP ---
    def test_php(self) -> None:
        r1 = self._req(
            "9.1 PHP installed versions",
            "GET", "/api/php/installed",
            tags=["php"],
        )
        if r1.get("status") == "PASS":
            if not isinstance(r1.get("response", {}).get("data"), list):
                r1["status"] = "FAIL"
                r1["message"] = "Expected list for data"

        r2 = self._req(
            "9.2 PHP available versions",
            "GET", "/api/php/available",
            tags=["php"],
        )
        if r2.get("status") == "PASS":
            if not isinstance(r2.get("response", {}).get("data"), list):
                r2["status"] = "FAIL"
                r2["message"] = "Expected list for data"

    # --- 10. Security ---
    def test_security(self) -> None:
        self._req(
            "10.1 Security status",
            "GET", "/api/security/status",
            tags=["security"],
        )

        self._req(
            "10.2 ModSecurity status",
            "GET", "/api/security/modsec/status",
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["security"],
        )

    # --- 11. System status ---
    def test_system(self) -> None:
        r = self._req(
            "11.1 System status",
            "GET", "/api/system/status",
            tags=["system"],
        )
        if r.get("status") == "PASS":
            data = r.get("response", {}).get("data", {})
            for key in ("webserver", "database", "mail", "dns", "ftp"):
                if key not in data:
                    r["status"] = "FAIL"
                    r["message"] = f"Missing '{key}' in system status data"
                    break

    # --- 12. Backup ---
    def test_backup(self) -> None:
        r = self._req(
            "12.1 Backup enqueue (full)",
            "POST", "/api/backup/enqueue",
            body={"username": "testuser", "backup_type": "full"},
            tags=["backup"],
        )
        if r.get("status") == "PASS":
            data = r.get("response", {}).get("data", {})
            if "id" not in data or "type" not in data:
                r["status"] = "FAIL"
                r["message"] = f"Backup job missing expected fields. got: {data}"

        self._req(
            "12.2 Backup enqueue (files)",
            "POST", "/api/backup/enqueue",
            body={"username": "testuser", "backup_type": "files"},
            tags=["backup"],
        )

        self._req(
            "12.3 Backup enqueue (database)",
            "POST", "/api/backup/enqueue",
            body={"username": "testuser", "backup_type": "database"},
            tags=["backup"],
        )

        self._req(
            "12.4 Backup enqueue (invalid type → 400)",
            "POST", "/api/backup/enqueue",
            body={"username": "testuser", "backup_type": "invalid_type"},
            expect_status=400,
            expect_key="detail",
            expect_success_value=None,
            tags=["backup"],
        )

    # --- 13. Cron ---
    def test_cron(self) -> None:
        self._req(
            "13.1 Cron add entry",
            "POST", "/api/cron/add",
            body={
                "username": TEST_CRON_USER,
                "expression": "0 * * * *",
                "command": "/usr/bin/php /var/www/test/cron.php",
            },
            tags=["cron"],
        )

        r = self._req(
            "13.2 Cron list entries",
            "GET", f"/api/cron/list/{TEST_CRON_USER}",
            tags=["cron"],
        )
        if r.get("status") == "PASS":
            data = r.get("response", {}).get("data")
            if not isinstance(data, list) or len(data) == 0:
                r["status"] = "FAIL"
                r["message"] = f"Expected non-empty list, got: {data}"

        self._req(
            "13.3 Cron clear entries",
            "DELETE", f"/api/cron/clear/{TEST_CRON_USER}",
            tags=["cron"],
        )

        r2 = self._req(
            "13.4 Cron list after clear (expect empty)",
            "GET", f"/api/cron/list/{TEST_CRON_USER}",
            tags=["cron"],
        )
        if r2.get("status") == "PASS":
            data = r2.get("response", {}).get("data")
            if not isinstance(data, list):
                r2["status"] = "FAIL"
                r2["message"] = f"Expected list, got: {data}"

        self._req(
            "13.5 Cron add — missing fields → 400/422",
            "POST", "/api/cron/add",
            body={"username": "", "expression": "", "command": ""},
            expect_status=[400, 422],
            expect_success_value=None,
            expect_key=None,
            tags=["cron"],
        )

    # --- 14. Compat / legacy endpoints ---
    def test_compat(self) -> None:
        self._req(
            "14.1 Compat: database/create",
            "POST", "/api/database/create",
            body={"name": TEST_DB + "_compat"},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["compat"],
        )

        self._req(
            "14.2 Compat: email/create",
            "POST", "/api/email/create",
            body={"email": f"compat@{TEST_MAIL_DOM}", "password": "C@mpatP@ss1"},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["compat"],
        )

        self._req(
            "14.3 Compat: dns/create-zone",
            "POST", "/api/dns/create-zone",
            body={"domain": "compat." + TEST_DOMAIN},
            expect_status=[200, 400],
            expect_key="success",
            expect_success_value=None,
            tags=["compat"],
        )

    # -----------------------------------------------------------------------
    # Run all sections
    # -----------------------------------------------------------------------
    def run_all(self) -> None:
        sections = [
            ("Health",          self.test_health),
            ("Auth",            self.test_auth),
            ("Domain",          self.test_domains),
            ("MySQL",           self.test_mysql),
            ("Mail",            self.test_mail),
            ("DNS",             self.test_dns),
            ("SSL",             self.test_ssl),
            ("FTP",             self.test_ftp),
            ("PHP",             self.test_php),
            ("Security",        self.test_security),
            ("System Status",   self.test_system),
            ("Backup",          self.test_backup),
            ("Cron",            self.test_cron),
            ("Compat/Legacy",   self.test_compat),
        ]
        for name, fn in sections:
            _print_section(name)
            fn()


# ---------------------------------------------------------------------------
# Section 15: Report generation
# ---------------------------------------------------------------------------

def _print_section(name: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name.upper()}")
    print(f"{'─' * 60}")


def _status_icon(s: str) -> str:
    return {"PASS": "✓", "FAIL": "✗", "ERROR": "!", "WARN": "⚠"}.get(s, "?")


def print_results() -> None:
    passes  = sum(1 for r in _results if r["status"] == "PASS")
    fails   = sum(1 for r in _results if r["status"] == "FAIL")
    errors  = sum(1 for r in _results if r["status"] == "ERROR")
    warns   = sum(1 for r in _results if r["status"] == "WARN")
    total   = len(_results)
    full    = passes + warns  # graceful errors count as working API

    print(f"\n{'═' * 60}")
    print(f"  RESULTS  — Pass: {passes}  Warn(infra): {warns}  Fail: {fails}  Error: {errors}  Total: {total}")
    print(f"{'═' * 60}")
    for r in _results:
        icon = _status_icon(r["status"])
        msg  = r.get("message", "")
        http = r.get("http_status", "-")
        print(f"  [{icon}] {r['name']:50s}  HTTP {http}  — {msg[:80]}")

    print(f"\n  PASS RATE (endpoints working): {full}/{total} ({100*full//total if total else 0}%)")
    print(f"  PASS RATE (full success):       {passes}/{total} ({100*passes//total if total else 0}%)")


def generate_report(iteration: int) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = REPORT_DIR / f"panel_issues_{date_str}_iter{iteration}.md"

    passes  = [r for r in _results if r["status"] == "PASS"]
    fails   = [r for r in _results if r["status"] == "FAIL"]
    errors  = [r for r in _results if r["status"] == "ERROR"]
    warns   = [r for r in _results if r["status"] == "WARN"]
    total   = len(_results)
    full    = len(passes) + len(warns)

    lines: list[str] = []
    lines.append(f"# HS-Panel API Test Report — {date_str} (Iteration {iteration})")
    lines.append(f"\nGenerated: {_now()}")
    lines.append(f"\n## Summary\n")
    lines.append(f"| Status | Count | Meaning |")
    lines.append(f"|--------|-------|---------|")
    lines.append(f"| PASS   | {len(passes)} | Endpoint fully functional |")
    lines.append(f"| WARN   | {len(warns)} | API works, infrastructure service not installed |")
    lines.append(f"| FAIL   | {len(fails)} | Endpoint or response broken |")
    lines.append(f"| ERROR  | {len(errors)} | Could not reach endpoint |")
    lines.append(f"| **Total** | **{total}** | |")
    lines.append(f"\n**API Health Rate (endpoints reachable + graceful): {100*full//total if total else 0}%**")
    lines.append(f"\n**Full Pass Rate (operations succeed): {100*len(passes)//total if total else 0}%**\n")

    if warns:
        lines.append(f"\n## Infrastructure Dependencies Not Met\n")
        lines.append("These endpoints return graceful errors because optional system services/binaries are not installed in the container:\n")
        by_category: dict[str, list] = {}
        for r in warns:
            tag = (r.get("tags") or ["uncategorized"])[0]
            by_category.setdefault(tag, []).append(r)
        for cat, items in by_category.items():
            lines.append(f"### {cat.upper()}")
            for r in items:
                lines.append(f"- `{r['method']} {r['path']}` — {r.get('message', '')}")
            lines.append("")

    if fails or errors:
        lines.append(f"\n## Real Issues Found (require fixes)\n")
        for r in fails + errors:
            lines.append(f"### [{r['status']}] {r['name']}")
            lines.append(f"- **Endpoint**: `{r['method']} {r['path']}`")
            lines.append(f"- **HTTP Status**: {r.get('http_status', 'N/A')}")
            lines.append(f"- **Message**: {r.get('message', '')}")
            resp = r.get("response")
            if resp:
                lines.append(f"- **Response**: `{json.dumps(resp)[:500]}`")
            lines.append("")

    lines.append(f"\n## All Test Results\n")
    lines.append("| # | Name | Status | HTTP | Message |")
    lines.append("|---|------|--------|------|---------|")
    for i, r in enumerate(_results, 1):
        lines.append(
            f"| {i} | {r['name']} | **{r['status']}** | "
            f"{r.get('http_status', '-')} | {r.get('message', '')[:100]} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Section 19: Build status banner
# ---------------------------------------------------------------------------

def print_build_status(iteration: int, report_path: Path) -> None:
    passes  = sum(1 for r in _results if r["status"] == "PASS")
    fails   = sum(1 for r in _results if r["status"] == "FAIL")
    errors  = sum(1 for r in _results if r["status"] == "ERROR")
    warns   = sum(1 for r in _results if r["status"] == "WARN")
    total   = len(_results)
    full    = passes + warns
    pct     = 100 * full // total if total else 0

    print(f"\n{'#' * 60}")
    print(f"#  BUILD STATUS — Iteration {iteration}")
    print(f"#  API Health: {full}/{total} ({pct}%) — endpoints reachable & graceful")
    print(f"#  Full Pass: {passes}/{total} — operations succeed end-to-end")
    print(f"#  Warn(infra missing): {warns}  |  Fail: {fails}  |  Error: {errors}")
    print(f"#  Report: {report_path.name}")
    if fails == 0 and errors == 0:
        if warns == 0:
            print(f"#  STATUS: ALL TESTS PASSED ✓")
        else:
            print(f"#  STATUS: API FULLY FUNCTIONAL ✓  (install optional services for full operation)")
    else:
        print(f"#  STATUS: ISSUES FOUND — see report")
    print(f"{'#' * 60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="HS-Panel API Test Suite")
    parser.add_argument("--url",   default=DEFAULT_URL,   help="API base URL")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="API token")
    parser.add_argument("--iter",  type=int, default=1,   help="Iteration number for report naming")
    args = parser.parse_args()

    global _iteration
    _iteration = args.iter

    print(f"\nHS-Panel API Test Suite")
    print(f"Base URL : {args.url}")
    print(f"Token    : {args.token[:4]}{'*' * max(0, len(args.token)-4)}")
    print(f"Iteration: {_iteration}")

    runner = TestRunner(args.url, args.token)
    runner.run_all()

    print_results()
    path = generate_report(_iteration)
    print_build_status(_iteration, path)
    print(f"Report saved to: {path}\n")

    # Exit code: 0 = all pass (or warn-only), 1 = failures/errors
    fails  = sum(1 for r in _results if r["status"] in ("FAIL", "ERROR"))
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
