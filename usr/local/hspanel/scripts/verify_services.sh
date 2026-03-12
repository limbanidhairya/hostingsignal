#!/usr/bin/env bash
###############################################################################
# HostingSignal — Service Verification Script
# Checks every required service and prints pass/fail with fix hints.
###############################################################################

set -uo pipefail

PASS=0
FAIL=0
WARN=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[PASS]${NC} $*"; ((PASS++)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $*"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; ((WARN++)); }
info() { echo -e "  ${BLUE}[INFO]${NC} $*"; }

check_binary() {
  local name="$1"
  local bin="$2"
  local fix="$3"
  if command -v "${bin}" >/dev/null 2>&1; then
    ok "${name} binary found: $(command -v "${bin}")"
  else
    fail "${name} binary '${bin}' not found. Fix: ${fix}"
  fi
}

check_service() {
  local label="$1"
  local svc="$2"
  local fix="$3"

  if ! command -v systemctl >/dev/null 2>&1; then
    warn "systemctl not available, skipping service check for ${label}"
    return
  fi

  if systemctl is-active --quiet "${svc}" 2>/dev/null; then
    ok "${label} (${svc}) is running"
  elif systemctl is-enabled --quiet "${svc}" 2>/dev/null; then
    warn "${label} (${svc}) is enabled but not running. Fix: systemctl start ${svc}"
  else
    fail "${label} (${svc}) not found or not enabled. Fix: ${fix}"
  fi
}

check_port() {
  local label="$1"
  local port="$2"
  local fix="$3"

  if command -v ss >/dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
      ok "${label} listening on port ${port}"
    else
      warn "${label} port ${port} not open. Fix: ${fix}"
    fi
  elif command -v netstat >/dev/null 2>&1; then
    if netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
      ok "${label} listening on port ${port}"
    else
      warn "${label} port ${port} not open. Fix: ${fix}"
    fi
  else
    info "Cannot check port ${port} (no ss/netstat available)"
  fi
}

check_dir() {
  local label="$1"
  local path="$2"
  local fix="$3"
  if [[ -d "${path}" ]]; then
    ok "${label} directory exists: ${path}"
  else
    fail "${label} directory missing: ${path}. Fix: ${fix}"
  fi
}

check_file() {
  local label="$1"
  local path="$2"
  local fix="$3"
  if [[ -f "${path}" ]]; then
    ok "${label} file exists: ${path}"
  else
    warn "${label} file missing: ${path}. Fix: ${fix}"
  fi
}

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  HostingSignal — Full Stack Service Verification"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── Web Server: OpenLiteSpeed ──────────────────────────────────────────────
echo -e "${BLUE}[ Web Server ]${NC}"
check_binary "OpenLiteSpeed" "lshttpd" "sudo ./install.sh --mode install --web-stack openlitespeed"
check_service "OpenLiteSpeed" "lsws" "sudo systemctl enable --now lsws"
check_port "OpenLiteSpeed HTTP" 80 "sudo systemctl start lsws"
check_port "OpenLiteSpeed HTTPS" 443 "sudo systemctl start lsws"
check_port "OLS Admin console" 7080 "sudo systemctl start lsws"
check_dir "OLS server root" "/usr/local/lsws" "sudo ./install.sh --mode install"
check_file "OLS config" "/usr/local/lsws/conf/httpd_config.conf" "OLS not installed correctly"

echo ""

# ── Database ──────────────────────────────────────────────────────────────
echo -e "${BLUE}[ Database ]${NC}"
CHECK_MARIADB=false
CHECK_MYSQL=false
if command -v mysqld >/dev/null 2>&1 || command -v mariadbd >/dev/null 2>&1; then
  CHECK_MARIADB=true
fi
if command -v mysqld >/dev/null 2>&1; then
  CHECK_MYSQL=true
fi

check_binary "MySQL/MariaDB client" "mysql" "sudo ./install.sh --mode install --db-engine mariadb"

if systemctl is-active --quiet mariadb 2>/dev/null; then
  ok "MariaDB service is running"
elif systemctl is-active --quiet mysql 2>/dev/null; then
  ok "MySQL service is running"
elif systemctl is-active --quiet mysqld 2>/dev/null; then
  ok "mysqld service is running"
else
  fail "No active MariaDB/MySQL service found. Fix: sudo systemctl enable --now mariadb"
fi

check_port "MySQL/MariaDB" 3306 "sudo systemctl start mariadb"

check_dir "phpMyAdmin" "/usr/local/hspanel/software/phpmyadmin" "sudo ./install.sh --mode configure"
check_file "phpMyAdmin index" "/usr/local/hspanel/software/phpmyadmin/index.php" "Re-run stage + configure"

echo ""

# ── Cache: LSCache (built into OLS) ───────────────────────────────────────
echo -e "${BLUE}[ Cache — LSCache ]${NC}"
if [[ -d "/usr/local/lsws/lsphp83" ]] || [[ -d "/usr/local/lsws/lsphp82" ]]; then
  ok "LSCache support present via OLS PHP handler"
else
  warn "LSCache: no OLS LSPHP handler found. LSCache requires OpenLiteSpeed + LSPHP packages."
fi

echo ""

# ── Email ──────────────────────────────────────────────────────────────────
echo -e "${BLUE}[ Email ]${NC}"
check_binary "Postfix" "postfix" "sudo ./install.sh --mode install"
check_binary "Dovecot" "dovecot" "sudo ./install.sh --mode install"
check_service "Postfix" "postfix" "sudo systemctl enable --now postfix"
check_service "Dovecot" "dovecot" "sudo systemctl enable --now dovecot"
check_port "SMTP" 25 "sudo systemctl start postfix"
check_port "SMTPS" 587 "Postfix TLS config needed"
check_port "IMAP" 143 "sudo systemctl start dovecot"
check_port "IMAPS" 993 "Dovecot IMAPS config needed"
check_dir "Rainloop Webmail" "/usr/local/hspanel/software/rainloop" "sudo ./install.sh --mode configure"

echo ""

# ── DNS: PowerDNS ─────────────────────────────────────────────────────────
echo -e "${BLUE}[ DNS — PowerDNS ]${NC}"
check_binary "PowerDNS" "pdns_server" "sudo ./install.sh --mode install"
check_service "PowerDNS" "pdns" "sudo systemctl enable --now pdns"
check_port "DNS (UDP/TCP)" 53 "sudo systemctl start pdns"

echo ""

# ── Security ──────────────────────────────────────────────────────────────
echo -e "${BLUE}[ Security ]${NC}"

# CSF
if command -v csf >/dev/null 2>&1; then
  ok "CSF firewall installed"
  if [[ -f /etc/csf/csf.conf ]]; then
    ok "CSF config present"
    if grep -q "TESTING = \"1\"" /etc/csf/csf.conf 2>/dev/null; then
      warn "CSF is in TESTING mode. Run: csf -e  to enable"
    else
      ok "CSF testing mode disabled (enforcing)"
    fi
  fi
else
  fail "CSF not installed. Fix: sudo ./usr/local/hspanel/scripts/manage_security.sh install csf"
fi

# ModSecurity
MOD_SEC_FOUND=false
for path in /etc/modsecurity /usr/share/modsecurity-crs /etc/modsec; do
  if [[ -d "${path}" ]]; then
    MOD_SEC_FOUND=true
    ok "ModSecurity found at ${path}"
    break
  fi
done
if [[ "${MOD_SEC_FOUND}" == "false" ]]; then
  fail "ModSecurity not found. Fix: sudo ./usr/local/hspanel/scripts/manage_security.sh install modsecurity"
fi

# ImunifyAV
if command -v imunify-antivirus >/dev/null 2>&1; then
  ok "ImunifyAV installed"
elif command -v imunifyav >/dev/null 2>&1; then
  ok "ImunifyAV installed"
else
  warn "ImunifyAV not installed. Fix: sudo ./usr/local/hspanel/scripts/manage_security.sh install imunifyav"
fi

echo ""

# ── FTP: Pure-FTPd ────────────────────────────────────────────────────────
echo -e "${BLUE}[ FTP — Pure-FTPd ]${NC}"
check_binary "Pure-FTPd" "pure-ftpd" "sudo ./install.sh --mode install"
check_service "Pure-FTPd" "pure-ftpd" "sudo systemctl enable --now pure-ftpd"
check_port "FTP" 21 "sudo systemctl start pure-ftpd"

echo ""

# ── PHP ───────────────────────────────────────────────────────────────────
echo -e "${BLUE}[ PHP — Multi-version ]${NC}"
for ver in 81 82 83; do
  lsphp_bin="/usr/local/lsws/lsphp${ver}/bin/php"
  label="lsphp${ver}"
  if [[ -x "${lsphp_bin}" ]]; then
    actual_ver=$("${lsphp_bin}" -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' 2>/dev/null || echo "?")
    ok "OLS LSPHP ${ver} present (PHP ${actual_ver}): ${lsphp_bin}"
  else
    warn "${label} OLS handler not found. Fix: sudo ./usr/local/hspanel/scripts/manage_php.sh install ${ver/8/8.}"
  fi
done

echo ""

# ── DevOps Tools ──────────────────────────────────────────────────────────
echo -e "${BLUE}[ DevOps Tools ]${NC}"
check_binary "Docker" "docker" "sudo ./install.sh --mode install"
check_service "Docker" "docker" "sudo systemctl enable --now docker"
check_binary "Git" "git" "sudo ./install.sh --mode install"
check_binary "Certbot (Let's Encrypt)" "certbot" "sudo ./install.sh --mode install"

echo ""

# ── Panel Core Paths ──────────────────────────────────────────────────────
echo -e "${BLUE}[ Panel Core Paths ]${NC}"
check_dir "Panel root" "/usr/local/hspanel" "sudo ./install.sh --mode configure"
check_dir "Panel var" "/var/hspanel" "sudo ./install.sh --mode configure"
check_dir "Queue" "/var/hspanel/queue/done" "sudo ./install.sh --mode configure"
check_dir "Users" "/var/hspanel/users" "sudo ./install.sh --mode configure"
check_dir "Userdata" "/var/hspanel/userdata" "sudo ./install.sh --mode configure"
check_file "Service config" "/usr/local/hspanel/config/services.env" "sudo ./install.sh --mode configure"

echo ""

# ── Summary ───────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL + WARN))
echo "═══════════════════════════════════════════════════════"
echo -e "  Results: ${GREEN}${PASS} PASS${NC}  ${RED}${FAIL} FAIL${NC}  ${YELLOW}${WARN} WARN${NC}  (${TOTAL} checks)"
echo "═══════════════════════════════════════════════════════"

if [[ "${FAIL}" -gt 0 ]]; then
  echo ""
  echo "  Some required services are missing. Typical full install:"
  echo "    sudo ./install.sh --mode all"
  echo ""
  exit 1
else
  echo ""
  echo "  All critical services verified."
  echo ""
  exit 0
fi
