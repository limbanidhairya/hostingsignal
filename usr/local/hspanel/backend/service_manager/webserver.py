"""
service_manager/webserver.py — OpenLiteSpeed / LiteSpeed Enterprise manager
Manages vhosts, PHP pools, SSL bindings, and OLS config rebuilds.
"""
from __future__ import annotations

import os
import re
import logging
from pathlib import Path

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

OLS_ROOT        = "/usr/local/lsws"
OLS_BIN         = f"{OLS_ROOT}/bin/lswsctrl"
VHOST_CONF_DIR  = f"{OLS_ROOT}/conf/vhosts"
OLS_CONF        = f"{OLS_ROOT}/conf/httpd_config.conf"
DEFAULT_PHP     = "lsphp83"
PHP_BIN_DIR     = f"{OLS_ROOT}"
DOCROOT_BASE    = "/var/www"


class WebServerManager(BaseServiceManager):
    """Manage OpenLiteSpeed virtual hosts and PHP bindings."""

    # ------------------------------------------------------------------
    # Service control
    # ------------------------------------------------------------------
    def restart(self) -> ServiceResult:
        rc, out, err = self._run([OLS_BIN, "restart"])
        return ServiceResult(rc == 0, out or err)

    def reload(self) -> ServiceResult:
        rc, out, err = self._run([OLS_BIN, "restart"])
        return ServiceResult(rc == 0, out or err)

    def start(self) -> ServiceResult:
        rc, out, err = self._run([OLS_BIN, "start"])
        return ServiceResult(rc == 0, out or err)

    def stop(self) -> ServiceResult:
        rc, out, err = self._run([OLS_BIN, "stop"])
        return ServiceResult(rc == 0, out or err)

    def status(self) -> dict:
        rc, out, err = self._run([OLS_BIN, "status"])
        active = rc == 0 and "running" in out.lower()
        return {"active": active, "output": out or err}

    # ------------------------------------------------------------------
    # Virtual host management
    # ------------------------------------------------------------------
    def create_vhost(
        self,
        domain: str,
        php_version: str = DEFAULT_PHP,
        docroot: str | None = None,
        ssl_cert: str | None = None,
        ssl_key: str | None = None,
    ) -> ServiceResult:
        """Create an OLS vhost config and docroot directory."""

        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain name: {domain}")

        docroot = docroot or f"{DOCROOT_BASE}/{domain}/public_html"
        conf_file = Path(VHOST_CONF_DIR) / domain / "vhconf.conf"
        conf_file.parent.mkdir(parents=True, exist_ok=True)

        # Create docroot
        Path(docroot).mkdir(parents=True, exist_ok=True)
        Path(f"{DOCROOT_BASE}/{domain}/logs").mkdir(parents=True, exist_ok=True)

        # Write default index.html if missing
        index_file = Path(docroot) / "index.html"
        if not index_file.exists():
            index_file.write_text(
                f"<html><body><h1>{domain} — Hosted by HS-Panel</h1></body></html>"
            )

        # Resolve PHP binary
        php_bin = self._resolve_php_bin(php_version)
        ssl_block = self._build_ssl_block(domain, ssl_cert, ssl_key) if ssl_cert else ""

        vhost_conf = self._render_vhost_conf(domain, docroot, php_bin, ssl_block)
        conf_file.write_text(vhost_conf)

        # Register vhost in httpd_config.conf
        reg_result = self._register_vhost_in_main_conf(domain, str(conf_file))
        if not reg_result.success:
            return reg_result

        reload_result = self.reload()
        return ServiceResult(
            True,
            f"Virtual host created: {domain}",
            {
                "domain": domain,
                "docroot": docroot,
                "conf_file": str(conf_file),
                "php_version": php_version,
                "reload": reload_result.message,
            },
        )

    def delete_vhost(self, domain: str) -> ServiceResult:
        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain name: {domain}")

        conf_dir = Path(VHOST_CONF_DIR) / domain
        if conf_dir.exists():
            import shutil
            shutil.rmtree(conf_dir)

        self._unregister_vhost_from_main_conf(domain)
        self.reload()
        return ServiceResult(True, f"Virtual host deleted: {domain}")

    def list_vhosts(self) -> list[dict]:
        vhosts = []
        base = Path(VHOST_CONF_DIR)
        if not base.exists():
            return vhosts
        for entry in base.iterdir():
            if entry.is_dir():
                conf = entry / "vhconf.conf"
                docroot = f"{DOCROOT_BASE}/{entry.name}/public_html"
                vhosts.append({
                    "domain": entry.name,
                    "conf_file": str(conf),
                    "conf_exists": conf.exists(),
                    "docroot": docroot,
                    "docroot_exists": Path(docroot).exists(),
                })
        return vhosts

    # ------------------------------------------------------------------
    # PHP version management
    # ------------------------------------------------------------------
    def get_available_php_versions(self) -> list[str]:
        versions = []
        ols_path = Path(OLS_ROOT)
        if ols_path.exists():
            for item in ols_path.iterdir():
                if item.name.startswith("lsphp") and item.is_dir():
                    versions.append(item.name)
        return sorted(versions)

    def _resolve_php_bin(self, php_version: str) -> str:
        php_bin = f"{OLS_ROOT}/{php_version}/bin/php"
        if not Path(php_bin).exists():
            php_bin = f"{OLS_ROOT}/{DEFAULT_PHP}/bin/php"
        return php_bin

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _render_vhost_conf(
        self, domain: str, docroot: str, php_bin: str, ssl_block: str
    ) -> str:
        return f"""# HS-Panel managed vhost — do not edit manually
# Domain: {domain}

docRoot                   {docroot}
vhDomain                  {domain}
vhAliases                 www.{domain}
adminEmails               admin@{domain}
enableGzip                1
enableIpGeo               1

errorlog {DOCROOT_BASE}/{domain}/logs/error.log {{
  useServer               0
  logLevel                WARN
  rollingSize             10M
}}

accesslog {DOCROOT_BASE}/{domain}/logs/access.log {{
  useServer               0
  rollingSize             10M
  keepDays                30
}}

index  {{
  useServer               0
  indexFiles              index.php, index.html
  autoIndex               0
}}

scripthandler  {{
  add                     lsapi:{domain}_lsphp php
}}

extprocessor {domain}_lsphp {{
  type                    lsapi
  address                 uds://tmp/lshttpd/{domain}.sock
  maxCons                 35
  env                     PHP_LSAPI_CHILDREN=35
  initTimeout             60
  retryTimeout            0
  persistConn             1
  respBuffer              0
  autoStart               1
  path                    {php_bin}
  backlog                 100
  instances               1
  extUser                 nobody
  extGroup                nobody
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}}

rewrite  {{
  enable                  1
  autoLoadHtaccess        1
}}

{ssl_block}
"""

    def _build_ssl_block(
        self, domain: str, ssl_cert: str, ssl_key: str
    ) -> str:
        return f"""
vhssl  {{
  keyFile                 {ssl_key}
  certFile                {ssl_cert}
  certChain               1
  sslProtocol             24
  enableECDHE             1
  enableDHE               1
}}
"""

    def _register_vhost_in_main_conf(
        self, domain: str, conf_file: str
    ) -> ServiceResult:
        main_conf = Path(OLS_CONF)
        if not main_conf.exists():
            return ServiceResult(True, "Main conf not found — skip registration")
        content = main_conf.read_text()
        marker = f"# vhost:{domain}"
        if marker in content:
            return ServiceResult(True, "Already registered")
        entry = (
            f"\n{marker}\n"
            f"virtualhost {domain} {{\n"
            f"  vhRoot                  {DOCROOT_BASE}/{domain}/\n"
            f"  configFile              {conf_file}\n"
            f"  allowSymbolLink         1\n"
            f"  enableScript            1\n"
            f"  restrained              0\n"
            f"  maxKeepAliveReq         500\n"
            f"}}\n"
        )
        main_conf.write_text(content + entry)
        return ServiceResult(True, f"vhost {domain} registered in main conf")

    def _unregister_vhost_from_main_conf(self, domain: str) -> None:
        main_conf = Path(OLS_CONF)
        if not main_conf.exists():
            return
        content = main_conf.read_text()
        pattern = rf"# vhost:{re.escape(domain)}\nvirtualhost {re.escape(domain)} \{{[^}}]*\}}\n"
        content = re.sub(pattern, "", content, flags=re.DOTALL)
        main_conf.write_text(content)

    @staticmethod
    def _validate_domain(domain: str) -> bool:
        pattern = r'^(?!-)[A-Za-z0-9\-]{1,63}(?<!-)(\.[A-Za-z0-9\-]{1,63})+$'
        return bool(re.match(pattern, domain))
