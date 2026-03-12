#!/usr/bin/env bash
###############################################################################
# HS-Panel Universal Installer v2.0
# Service-First, CyberPanel-aligned architecture
#
# Supported OS:
#   Ubuntu 22.04, Ubuntu 24.04, Debian 12
#   AlmaLinux 8/9, CentOS 8 Stream
#
# Usage:
#   bash install.sh [--mode all|stage|install|configure|upgrade]
#                   [--db mariadb|mysql] [--web openlitespeed|lsws]
#                   [--panel-password <pw>] [--admin-email <email>]
#                   [--skip-firewall] [--dry-run]
###############################################################################
set -euo pipefail

INSTALLER_VERSION="2.0.0"
PANEL_ROOT="/usr/local/hspanel"
PANEL_VAR="/var/hspanel"
PANEL_USER="hspanel"
PANEL_GROUP="hspanel"
PANEL_API_PORT=2083
PANEL_UI_PORT=2086
LOG_FILE="/var/log/hspanel-install.log"

MODE="all"; DB_ENGINE="mariadb"; WEB_STACK="openlitespeed"
USE_ENTERPRISE_LSWS="false"; SKIP_FIREWALL="false"
DRY_RUN="false"; ADMIN_EMAIL=""; PANEL_PASSWORD=""
OS_ID=""; OS_VERSION=""; PKG_MGR=""

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[HS]${NC} $*" | tee -a "${LOG_FILE}"; }
info() { echo -e "${BLUE}[HS]${NC} $*"  | tee -a "${LOG_FILE}"; }
warn() { echo -e "${YELLOW}[HS][WARN]${NC} $*" | tee -a "${LOG_FILE}"; }
fail() { echo -e "${RED}[HS][FATAL]${NC} $*" | tee -a "${LOG_FILE}"; exit 1; }
step() { echo -e "\n${BOLD}${BLUE}━━━ $* ━━━${NC}" | tee -a "${LOG_FILE}"; }
dry()  { [[ "${DRY_RUN}" == "true" ]] && echo -e "${YELLOW}[DRY-RUN]${NC} $*" && return 0; return 1; }

usage() {
  cat <<EOF
HS-Panel Universal Installer ${INSTALLER_VERSION}
Usage: bash install.sh [options]
  --mode <all|stage|install|configure|upgrade>   Default: all
  --db   <mariadb|mysql>                          Default: mariadb
  --web  <openlitespeed|lsws>                     Default: openlitespeed
  --with-enterprise-lsws
  --panel-password <password>
  --admin-email    <email>
  --skip-firewall
  --dry-run
  --help
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)            MODE="$2";            shift 2 ;;
      --db)              DB_ENGINE="$2";       shift 2 ;;
      --web)             WEB_STACK="$2";       shift 2 ;;
      --with-enterprise-lsws) USE_ENTERPRISE_LSWS="true"; WEB_STACK="lsws"; shift ;;
      --panel-password)  PANEL_PASSWORD="$2";  shift 2 ;;
      --admin-email)     ADMIN_EMAIL="$2";     shift 2 ;;
      --skip-firewall)   SKIP_FIREWALL="true"; shift ;;
      --dry-run)         DRY_RUN="true";       shift ;;
      --help|-h)         usage; exit 0 ;;
      *) fail "Unknown argument: $1" ;;
    esac
  done
}

preflight() {
  step "Pre-flight checks"
  mkdir -p "$(dirname "${LOG_FILE}")"
  log "HS-Panel Installer ${INSTALLER_VERSION} -- $(date)"
  [[ "${EUID}" -ne 0 ]] && [[ "${MODE}" != "stage" ]] \
    && fail "Must run as root. Use: sudo bash install.sh"

  if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    OS_ID="${ID,,}"; OS_VERSION="${VERSION_ID}"
  else
    fail "Cannot detect OS -- /etc/os-release missing."
  fi

  case "${OS_ID}" in
    ubuntu|debian)         PKG_MGR="apt" ;;
    almalinux|rocky|centos|rhel) PKG_MGR="dnf" ;;
    *) fail "Unsupported OS: ${OS_ID} ${OS_VERSION}." ;;
  esac

  log "OS: ${OS_ID} ${OS_VERSION} (pkg: ${PKG_MGR})"
  log "Mode: ${MODE} | Web: ${WEB_STACK} | DB: ${DB_ENGINE}"

  local ram_mb
  ram_mb=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)
  [[ ${ram_mb} -lt 512 ]] && warn "Low RAM: ${ram_mb} MB (minimum recommended: 1024 MB)"

  [[ ! -f "${PANEL_ROOT}/config/.secrets" ]] && _generate_secrets
}

_generate_secrets() {
  mkdir -p "${PANEL_ROOT}/config"
  local s db p
  s=$(openssl rand -hex 32 2>/dev/null)
  db=$(openssl rand -base64 20 2>/dev/null | tr -d '/+=' | head -c 24)
  p=$(openssl rand -hex 16 2>/dev/null)
  cat > "${PANEL_ROOT}/config/.secrets" <<EOF
PANEL_SECRET_KEY=${s}
PANEL_DB_PASSWORD=${db}
PDNS_API_KEY=${p}
EOF
  chmod 600 "${PANEL_ROOT}/config/.secrets"
  log "Secrets generated at ${PANEL_ROOT}/config/.secrets"
}

_apt_install() {
  dry "apt-get install -y $1" && return 0
  apt-get install -y --no-install-recommends "$1" >>"${LOG_FILE}" 2>&1 \
    || { warn "Package not installed: $1"; return 1; }
}

_dnf_install() {
  dry "dnf install -y $1" && return 0
  dnf install -y --quiet "$1" >>"${LOG_FILE}" 2>&1 \
    || { warn "Package not installed: $1"; return 1; }
}

stage_artifacts() {
  step "Stage: Downloading artifacts"
  local DL="/var/cache/hspanel/downloads"
  mkdir -p "${DL}"
  _dl() {
    local url="$1" tgt="$2"
    [[ -f "${tgt}" ]] && { log "Cached: $(basename "${tgt}")"; return 0; }
    log "Downloading: $(basename "${tgt}")"
    curl -fsSL --retry 3 --retry-delay 2 -o "${tgt}" "${url}" >>"${LOG_FILE}" 2>&1 \
      || { warn "Download failed: ${url}"; return 1; }
  }
  _dl "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz" \
      "${DL}/phpmyadmin.tar.gz" || true
  _dl "https://github.com/coreruleset/coreruleset/archive/refs/heads/main.zip" \
      "${DL}/owasp-crs.zip" || true
  _dl "https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh" \
      "${DL}/imunifyav-install.sh" || true
  log "[Stage] Done"
}

install_system_deps() {
  step "Install: System dependencies"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >>"${LOG_FILE}" 2>&1
    for p in curl wget git unzip tar openssl build-essential gcc make \
              ca-certificates gnupg lsb-release software-properties-common \
              python3 python3-pip python3-venv \
              perl libio-socket-inet-perl libjson-perl \
              net-tools iproute2 procps; do
      _apt_install "${p}" || true
    done
  else
    for p in curl wget git unzip tar openssl gcc make ca-certificates gnupg \
              python3 python3-pip perl perl-JSON net-tools iproute procps-ng; do
      _dnf_install "${p}" || true
    done
  fi
  log "[Deps] Done"
}

install_webserver() {
  step "Install: Web server (${WEB_STACK})"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    if [[ ! -f /etc/apt/sources.list.d/lst_debian_repo.list ]] \
       && [[ ! -f /etc/apt/sources.list.d/lst_repo.list ]]; then
      curl -fsSL https://repo.litespeed.sh | bash >>"${LOG_FILE}" 2>&1 \
        || warn "Could not add OLS repo"
    fi
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >>"${LOG_FILE}" 2>&1
    for p in openlitespeed lsphp83 lsphp83-common lsphp83-mysql lsphp83-curl; do
      _apt_install "${p}" || warn "Could not install ${p}"
    done
    for p in lsphp83-xml lsphp83-zip lsphp83-mbstring lsphp83-imagick lsphp83-redis; do
      _apt_install "${p}" || true
    done
  else
    if [[ ! -f /etc/yum.repos.d/litespeed.repo ]]; then
      curl -fsSL https://repo.litespeed.sh | bash >>"${LOG_FILE}" 2>&1 || warn "OLS repo add failed"
    fi
    for p in openlitespeed lsphp83 lsphp83-common lsphp83-mysqlnd lsphp83-process \
              lsphp83-xml lsphp83-mbstring; do
      _dnf_install "${p}" || warn "Could not install ${p}"
    done
  fi
  systemctl enable lsws >>"${LOG_FILE}" 2>&1 \
    || systemctl enable --now lsws >>"${LOG_FILE}" 2>&1 || true
  log "[Webserver] Done"
}

install_database() {
  step "Install: Database (${DB_ENGINE})"
  local pkg="mariadb-server"
  [[ "${DB_ENGINE}" == "mysql" ]] && pkg="mysql-server"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    _apt_install "${pkg}"
  else
    _dnf_install "${pkg}"
  fi
  local svc
  svc=$(cut -d- -f1 <<< "${pkg}")
  systemctl enable --now "${svc}" >>"${LOG_FILE}" 2>&1 || true

  local tries=0
  while [[ ! -S /var/run/mysqld/mysqld.sock ]] && [[ ${tries} -lt 15 ]]; do
    sleep 2; ((tries++))
  done

  if [[ -S /var/run/mysqld/mysqld.sock ]]; then
    local db_pass
    db_pass=$(grep PANEL_DB_PASSWORD "${PANEL_ROOT}/config/.secrets" 2>/dev/null \
      | cut -d= -f2 || echo "changeme")
    mysql -u root <<SQL >>"${LOG_FILE}" 2>&1 || warn "Panel DB setup failed"
CREATE DATABASE IF NOT EXISTS hspanel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'hspanel'@'localhost' IDENTIFIED BY '${db_pass}';
GRANT ALL PRIVILEGES ON hspanel.* TO 'hspanel'@'localhost';
FLUSH PRIVILEGES;
SQL
    log "[Database] hspanel DB created"
  else
    warn "MySQL socket not found -- DB setup deferred"
  fi

  local DL="/var/cache/hspanel/downloads"
  mkdir -p "${PANEL_ROOT}/software/phpmyadmin"
  if [[ -f "${DL}/phpmyadmin.tar.gz" ]]; then
    tar -xzf "${DL}/phpmyadmin.tar.gz" -C "${PANEL_ROOT}/software/phpmyadmin" \
      --strip-components=1 >>"${LOG_FILE}" 2>&1 || warn "phpMyAdmin extract failed"
    log "[Database] phpMyAdmin deployed"
  fi
  log "[Database] Done"
}

install_mail_stack() {
  step "Install: Mail stack (Postfix + Dovecot)"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    echo "postfix postfix/mailname string $(hostname -f)" | debconf-set-selections
    echo "postfix postfix/main_mailer_type string 'Internet Site'" | debconf-set-selections
    for p in postfix postfix-mysql dovecot-core dovecot-imapd dovecot-pop3d \
              dovecot-mysql dovecot-lmtpd spamassassin; do
      _apt_install "${p}" || warn "Mail package missing: ${p}"
    done
  else
    for p in postfix dovecot spamassassin; do
      _dnf_install "${p}" || warn "Mail package missing: ${p}"
    done
  fi
  systemctl enable postfix dovecot >>"${LOG_FILE}" 2>&1 || true
  log "[Mail] Done"
}

install_dns() {
  step "Install: DNS (PowerDNS)"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >>"${LOG_FILE}" 2>&1
    _apt_install "pdns-server" || warn "PowerDNS install failed"
    _apt_install "pdns-backend-mysql" || warn "PowerDNS MySQL backend not installed"
  else
    _dnf_install "pdns" || warn "PowerDNS install failed"
    _dnf_install "pdns-backend-mysql" || true
  fi

  local pdns_key
  pdns_key=$(grep PDNS_API_KEY "${PANEL_ROOT}/config/.secrets" 2>/dev/null \
    | cut -d= -f2 || openssl rand -hex 16)
  mkdir -p /etc/powerdns
  cat > /etc/powerdns/pdns.conf <<EOF
launch=gmysql
gmysql-host=127.0.0.1
gmysql-user=pdns
gmysql-password=${pdns_key}
gmysql-dbname=pdns
api=yes
api-key=${pdns_key}
webserver=yes
webserver-address=127.0.0.1
webserver-port=8053
webserver-allow-from=127.0.0.1,::1
local-address=0.0.0.0
local-port=53
EOF
  chmod 640 /etc/powerdns/pdns.conf

  if mysql -u root -e "SELECT 1;" >/dev/null 2>&1; then
    mysql -u root <<SQL >>"${LOG_FILE}" 2>&1 || warn "pdns DB setup failed"
CREATE DATABASE IF NOT EXISTS pdns CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'pdns'@'localhost' IDENTIFIED BY '${pdns_key}';
GRANT ALL PRIVILEGES ON pdns.* TO 'pdns'@'localhost';
FLUSH PRIVILEGES;
SQL
    local schema
    schema=$(find /usr/share -name "schema.mysql.sql" 2>/dev/null | grep -i pdns | head -1)
    [[ -f "${schema}" ]] && mysql -u root pdns < "${schema}" >>"${LOG_FILE}" 2>&1 || true
  fi
  systemctl enable pdns >>"${LOG_FILE}" 2>&1 || true
  log "[DNS] Done"
}

install_security_tools() {
  [[ "${SKIP_FIREWALL}" == "true" ]] && { log "[Security] Skipped"; return 0; }
  step "Install: Security tools (CSF + ModSecurity)"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    for p in libwww-perl liblwp-protocol-https-perl libgd-dev; do
      _apt_install "${p}" || true
    done
    _apt_install "libapache2-mod-security2" || true
    _apt_install "modsecurity-crs" || true
  else
    _dnf_install "mod_security" || true
    _dnf_install "mod_security_crs" || true
  fi

  if [[ ! -d /etc/csf ]]; then
    local tmp; tmp=$(mktemp -d)
    if curl -fsSL https://download.configserver.com/csf.tgz -o "${tmp}/csf.tgz" >>"${LOG_FILE}" 2>&1; then
      tar -xzf "${tmp}/csf.tgz" -C "${tmp}" >>"${LOG_FILE}" 2>&1
      bash "${tmp}/csf/install.sh" >>"${LOG_FILE}" 2>&1 && log "CSF installed" || warn "CSF install failed"
    else
      warn "Could not download CSF"
    fi
    rm -rf "${tmp}"
  fi

  if [[ -f /etc/csf/csf.conf ]]; then
    sed -i "s/^TCP_IN = \"/TCP_IN = \"${PANEL_UI_PORT},${PANEL_API_PORT},/" /etc/csf/csf.conf || true
    csf -r >>"${LOG_FILE}" 2>&1 || true
  fi
  log "[Security] Done"
}

install_ftp() {
  step "Install: FTP (Pure-FTPd)"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    _apt_install pure-ftpd
    _apt_install pure-ftpd-mysql || true
  else
    _dnf_install pure-ftpd || warn "pure-ftpd not found; try EPEL"
  fi
  mkdir -p /etc/pure-ftpd/conf
  echo "yes" > /etc/pure-ftpd/conf/ChrootEveryone
  echo "yes" > /etc/pure-ftpd/conf/CreateHomeDir
  echo "1000" > /etc/pure-ftpd/conf/MinUID
  systemctl enable pure-ftpd >>"${LOG_FILE}" 2>&1 || true
  log "[FTP] Done"
}

install_docker_git() {
  step "Install: Docker and Git"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    command -v docker >/dev/null 2>&1 \
      || curl -fsSL https://get.docker.com | bash >>"${LOG_FILE}" 2>&1 \
      || _apt_install docker.io
    _apt_install git
  else
    command -v docker >/dev/null 2>&1 \
      || dnf install -y --quiet docker-ce docker-ce-cli containerd.io >>"${LOG_FILE}" 2>&1 \
      || _dnf_install docker
    _dnf_install git
  fi
  systemctl enable --now docker >>"${LOG_FILE}" 2>&1 || true
  id "${PANEL_USER}" >/dev/null 2>&1 && usermod -aG docker "${PANEL_USER}" || true
  log "[Docker] Done"
}

install_certbot() {
  step "Install: Certbot (Let's Encrypt)"
  if [[ "${PKG_MGR}" == "apt" ]]; then
    _apt_install certbot || _apt_install python3-certbot
  else
    _dnf_install certbot || true
  fi
  mkdir -p /var/www/letsencrypt/.well-known/acme-challenge
  log "[SSL] Certbot done"
}

configure_panel() {
  step "Configure: HS-Panel directories and system user"
  if ! id "${PANEL_USER}" >/dev/null 2>&1; then
    useradd -r -m -d "${PANEL_ROOT}" -s /usr/sbin/nologin \
      -c "HS-Panel Service Account" "${PANEL_USER}" >>"${LOG_FILE}" 2>&1 \
      || warn "Could not create ${PANEL_USER} user"
  fi

  mkdir -p \
    "${PANEL_ROOT}/backend/api" \
    "${PANEL_ROOT}/backend/service_manager" \
    "${PANEL_ROOT}/backend/installer" \
    "${PANEL_ROOT}/backend/configs" \
    "${PANEL_ROOT}/backend/models" \
    "${PANEL_ROOT}/config/ssl" \
    "${PANEL_ROOT}/logs" \
    "${PANEL_ROOT}/software/phpmyadmin" \
    "${PANEL_ROOT}/software/webmail" \
    "${PANEL_ROOT}/ui" \
    "${PANEL_VAR}/queue/done" \
    "${PANEL_VAR}/users" \
    "${PANEL_VAR}/userdata" \
    "${PANEL_VAR}/backups" \
    "${PANEL_VAR}/tmp"

  _write_hspanel_conf

  chown -R "${PANEL_USER}:${PANEL_GROUP}" "${PANEL_ROOT}" "${PANEL_VAR}" 2>/dev/null || true
  chmod 750 "${PANEL_ROOT}"
  chmod 700 "${PANEL_ROOT}/config"
  chmod 600 "${PANEL_ROOT}/config/.secrets"
  chmod 750 "${PANEL_VAR}/users" "${PANEL_VAR}/userdata"
  chmod 755 "${PANEL_VAR}/queue"

  # Compile setuid wrapper
  local sysop_c="${PANEL_ROOT}/bin/wrap_sysop.c"
  local sysop_bin="${PANEL_ROOT}/bin/wrap_sysop"
  if [[ -f "${sysop_c}" ]]; then
    gcc -O2 -o "${sysop_bin}" "${sysop_c}" >>"${LOG_FILE}" 2>&1 \
      && chmod 4755 "${sysop_bin}" \
      && chown root:root "${sysop_bin}" \
      && log "wrap_sysop compiled (4755)" \
      || warn "wrap_sysop compilation failed"
  fi

  # Python venv + backend deps
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "${PANEL_ROOT}/venv" >>"${LOG_FILE}" 2>&1 || true
    [[ -f "${PANEL_ROOT}/backend/requirements.txt" ]] \
      && "${PANEL_ROOT}/venv/bin/pip" install --quiet -r \
           "${PANEL_ROOT}/backend/requirements.txt" >>"${LOG_FILE}" 2>&1 \
      || warn "Backend Python deps not installed"
  fi

  log "[Configure] Done"
}

_write_hspanel_conf() {
  local tmpl="${PANEL_ROOT}/config/hspanel.conf"
  [[ ! -f "${tmpl}" ]] && return
  local secret db_pass pdns_key
  secret=$(grep  PANEL_SECRET_KEY  "${PANEL_ROOT}/config/.secrets" 2>/dev/null | cut -d= -f2 || openssl rand -hex 32)
  db_pass=$(grep PANEL_DB_PASSWORD "${PANEL_ROOT}/config/.secrets" 2>/dev/null | cut -d= -f2 || echo "changeme")
  pdns_key=$(grep PDNS_API_KEY     "${PANEL_ROOT}/config/.secrets" 2>/dev/null | cut -d= -f2 || openssl rand -hex 16)
  sed -i "s|REPLACE_WITH_GENERATED_SECRET|${secret}|g"  "${tmpl}" 2>/dev/null || true
  sed -i "s|REPLACE_WITH_DB_PASSWORD|${db_pass}|g"      "${tmpl}" 2>/dev/null || true
  sed -i "s|REPLACE_WITH_PDNS_API_KEY|${pdns_key}|g"    "${tmpl}" 2>/dev/null || true
}

configure_openlitespeed() {
  step "Configure: OpenLiteSpeed"
  [[ ! -d /usr/local/lsws ]] && { warn "OLS not found -- skipping"; return 0; }
  mkdir -p /usr/local/lsws/conf/vhosts /var/www/html
  [[ -f "${PANEL_ROOT}/ui/index.html" ]] \
    && cp "${PANEL_ROOT}/ui/index.html" /var/www/html/index.html \
    || echo "<h1>HS-Panel — Server Running</h1>" > /var/www/html/index.html
  /usr/local/lsws/bin/lswsctrl start >>"${LOG_FILE}" 2>&1 || true
  log "[OLS] Done"
}

configure_systemd_services() {
  step "Configure: systemd service units"
  cat > /etc/systemd/system/hspanel-api.service <<EOF
[Unit]
Description=HS-Panel Backend API
After=network.target mariadb.service
Wants=mariadb.service

[Service]
Type=exec
User=${PANEL_USER}
Group=${PANEL_GROUP}
WorkingDirectory=${PANEL_ROOT}/backend
Environment=HS_PANEL_ROOT=${PANEL_ROOT}
Environment=HS_PANEL_ENV=production
ExecStart=${PANEL_ROOT}/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port ${PANEL_API_PORT} --workers 2
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=append:${PANEL_ROOT}/logs/api.log
StandardError=append:${PANEL_ROOT}/logs/api-error.log
LimitNOFILE=65536
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=${PANEL_ROOT} ${PANEL_VAR}

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/hspanel-daemon.service <<EOF
[Unit]
Description=HS-Panel HTTP/UI Daemon
After=network.target hspanel-api.service

[Service]
Type=simple
User=root
WorkingDirectory=${PANEL_ROOT}
ExecStart=/usr/bin/perl ${PANEL_ROOT}/daemon/hs-srvd.pl
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=append:${PANEL_ROOT}/logs/daemon.log
StandardError=append:${PANEL_ROOT}/logs/daemon-error.log

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/hspanel-taskd.service <<EOF
[Unit]
Description=HS-Panel Task Queue Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PANEL_ROOT}
ExecStart=/usr/bin/perl ${PANEL_ROOT}/daemon/hs-taskd.pl
Restart=always
RestartSec=10
StandardOutput=append:${PANEL_ROOT}/logs/taskd.log
StandardError=append:${PANEL_ROOT}/logs/taskd-error.log

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  for svc in hspanel-api hspanel-daemon hspanel-taskd; do
    systemctl enable "${svc}" >>"${LOG_FILE}" 2>&1 \
      && log "Enabled: ${svc}" || warn "Could not enable ${svc}"
  done
  log "[Systemd] Done"
}

upgrade_panel() {
  step "Upgrade: HS-Panel"
  systemctl stop hspanel-api hspanel-daemon hspanel-taskd >>"${LOG_FILE}" 2>&1 || true
  cp -a "${PANEL_ROOT}/config" "${PANEL_ROOT}/config.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  configure_panel
  systemctl start hspanel-api hspanel-daemon hspanel-taskd >>"${LOG_FILE}" 2>&1 || true
  log "[Upgrade] Done"
}

print_summary() {
  local ip
  ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_SERVER_IP")
  echo ""
  echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${GREEN}║    HS-Panel Installation Complete!           ║${NC}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  Panel URL : ${BLUE}http://${ip}:${PANEL_UI_PORT}${NC}"
  echo -e "  API URL   : ${BLUE}http://127.0.0.1:${PANEL_API_PORT}${NC}"
  echo -e "  Log file  : ${LOG_FILE}"
  echo -e "  Config    : ${PANEL_ROOT}/config/hspanel.conf"
  echo ""
  echo -e "  Service Status:"
  for svc in hspanel-api hspanel-daemon hspanel-taskd lsws mariadb postfix dovecot pdns; do
    systemctl is-active --quiet "${svc}" 2>/dev/null \
      && echo -e "    ${GREEN}+${NC} ${svc}" \
      || echo -e "    ${YELLOW}o${NC} ${svc}"
  done
  echo ""
  echo -e "  Next: bash ${PANEL_ROOT}/scripts/verify_services.sh"
  echo ""
}

main() {
  parse_args "$@"
  mkdir -p "$(dirname "${LOG_FILE}")"
  preflight

  case "${MODE}" in
    stage)                 stage_artifacts ;;
    install)               install_system_deps; install_webserver; install_database
                           install_mail_stack; install_dns; install_security_tools
                           install_ftp; install_docker_git; install_certbot ;;
    configure)             configure_panel; configure_openlitespeed
                           configure_systemd_services ;;
    all)                   stage_artifacts
                           install_system_deps; install_webserver; install_database
                           install_mail_stack; install_dns; install_security_tools
                           install_ftp; install_docker_git; install_certbot
                           configure_panel; configure_openlitespeed
                           configure_systemd_services ;;
    upgrade)               upgrade_panel ;;
    *)                     fail "Invalid mode: ${MODE}" ;;
  esac

  log "Installer finished (mode: ${MODE})"
  [[ "${MODE}" == "all" || "${MODE}" == "configure" ]] && print_summary
}

main "$@"
