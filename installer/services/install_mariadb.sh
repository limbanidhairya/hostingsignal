#!/usr/bin/env bash
# HS-Panel Service Installer — MariaDB
# Installs MariaDB, creates the hspanel database and user.

MARIADB_ROOT_PASSWD="${MARIADB_ROOT_PASSWD:-}"
MARIADB_APP_DB="${MARIADB_APP_DB:-hspanel}"
MARIADB_APP_USER="${MARIADB_APP_USER:-hspanel_user}"
MARIADB_APP_PASSWD="${MARIADB_APP_PASSWD:-}"

install_mariadb() {
  log_info "Installing MariaDB..."

  # Generate passwords before any work so they are available throughout
  [[ -z "$MARIADB_ROOT_PASSWD" ]] && MARIADB_ROOT_PASSWD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"
  [[ -z "$MARIADB_APP_PASSWD"  ]] && MARIADB_APP_PASSWD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"

  # Full pre-install cleanup — resolves port conflicts, stale packages and
  # broken repo files before we install, so dpkg never fails mid-flight.
  _mariadb_pre_install_cleanup

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _install_mariadb_debian
  else
    _install_mariadb_rhel
  fi

  # Step 7 — reload systemd after fresh unit files were written by dpkg
  systemctl daemon-reload 2>/dev/null || true

  # Step 8 — enable and (re)start
  systemctl enable mariadb 2>/dev/null || true
  systemctl restart mariadb 2>/dev/null || true

  _secure_mariadb
  _create_hspanel_db

  # Step 9 — health check: verify port 3306 is listening
  _mariadb_health_check

  log_success "MariaDB installed and configured"
  mark_service_done "mariadb"
  rollback_stop_service "mariadb"
}

# ---------------------------------------------------------------------------
# _mariadb_pre_install_cleanup
# ---------------------------------------------------------------------------
# Runs the full 6-step cleanup before any package installation so that
# the dpkg post-install hook can always start mariadbd cleanly.
# ---------------------------------------------------------------------------
_mariadb_pre_install_cleanup() {
  # ── Step 1: detect what is holding port 3306 ──────────────────────────────
  local _port_pid=""
  if command -v lsof &>/dev/null; then
    _port_pid="$(lsof -i :3306 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
  fi
  if [[ -z "$_port_pid" ]]; then
    # lsof not available — fall back to ss
    _port_pid="$(ss -tulnp 2>/dev/null \
      | awk '/:3306 /{match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]; exit}' || true)"
  fi
  if [[ -n "$_port_pid" ]]; then
    log_warning "[MariaDB] Port 3306 already in use by PID ${_port_pid}"
  fi

  # ── Step 2: stop conflicting systemd services ──────────────────────────────
  for _svc in mysql mysqld mariadb; do
    systemctl stop "$_svc" 2>/dev/null || true
  done

  # ── Step 3: kill leftover processes ───────────────────────────────────────
  pkill -f mysqld 2>/dev/null || true
  pkill -f mysql  2>/dev/null || true
  sleep 1   # give processes a moment to exit

  # ── Step 4: always purge any existing MySQL/MariaDB packages ────────────
  if [[ "$OS_FAMILY" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get remove --purge -y \
      mariadb-server mariadb-client mariadb-common \
      mysql-server mysql-client mysql-common 2>/dev/null || true
    apt-get autoremove -y 2>/dev/null || true
  fi

  # ── Step 5: remove stale/broken repo list files ───────────────────────────
  if [[ "$OS_FAMILY" == "debian" ]]; then
    rm -f /etc/apt/sources.list.d/mariadb.list.old_* 2>/dev/null || true
    apt-get update -qq 2>/dev/null || true
  fi

  # ── Final port check after cleanup ────────────────────────────────────────
  if ss -tulnp 2>/dev/null | grep -q ':3306'; then
    log_warning "[MariaDB] Port 3306 still busy after cleanup — install may fail"
  else
    log_success "[MariaDB] Port 3306 is free — proceeding with installation"
  fi
}

# ── Step 6: install MariaDB cleanly ─────────────────────────────────────────
_install_mariadb_debian() {
  export DEBIAN_FRONTEND=noninteractive

  # Add MariaDB 10.11 official repo (idempotent — skips if key/list exists)
  curl -fsSL https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | \
    bash -s -- --mariadb-server-version="mariadb-10.11" > /dev/null 2>&1

  apt-get update -qq
  apt-get install -y mariadb-server mariadb-client
}

_install_mariadb_rhel() {
  cat > /etc/yum.repos.d/mariadb.repo <<'EOF'
[mariadb]
name = MariaDB
baseurl = https://downloads.mariadb.com/MariaDB/mariadb-10.11/yum/rhel/$releasever/$basearch
gpgkey= https://downloads.mariadb.com/MariaDB/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF
  dnf install -y MariaDB-server MariaDB-client --skip-broken
}

# ── Step 9: health check ─────────────────────────────────────────────────────
_mariadb_health_check() {
  local _up=false
  for _i in 1 2 3 4 5; do
    if ss -tulnp 2>/dev/null | grep -q ':3306'; then
      _up=true; break
    fi
    sleep 2
  done

  if $_up; then
    log_success "[MariaDB] Port 3306 is listening"
  else
    echo "[ERROR] MariaDB failed to start — port 3306 not listening"
    systemctl status mariadb --no-pager 2>/dev/null || true
    return 1
  fi
}

_secure_mariadb() {
  # Wait for socket
  local retries=15
  while (( retries-- > 0 )); do
    mysqladmin ping --silent 2>/dev/null && break || sleep 1
  done

  mysql -u root <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASSWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
SQL

  # Write ~/.my.cnf for later automated queries
  cat > /root/.my.cnf <<CNF
[client]
user=root
password=${MARIADB_ROOT_PASSWD}
CNF
  chmod 600 /root/.my.cnf
  log_success "MariaDB secured"
}

_create_hspanel_db() {
  mysql --defaults-file=/root/.my.cnf <<SQL
CREATE DATABASE IF NOT EXISTS \`${MARIADB_APP_DB}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MARIADB_APP_USER}'@'localhost'
  IDENTIFIED BY '${MARIADB_APP_PASSWD}';
GRANT ALL PRIVILEGES ON \`${MARIADB_APP_DB}\`.* TO '${MARIADB_APP_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
  log_success "Database '${MARIADB_APP_DB}' and user '${MARIADB_APP_USER}' created"
}
