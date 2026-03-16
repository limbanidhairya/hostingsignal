#!/usr/bin/env bash
# HS-Panel Service Installer — MariaDB
# Installs MariaDB, creates the hspanel database and user.

MARIADB_ROOT_PASSWD="${MARIADB_ROOT_PASSWD:-}"
MARIADB_APP_DB="${MARIADB_APP_DB:-hspanel}"
MARIADB_APP_USER="${MARIADB_APP_USER:-hspanel_user}"
MARIADB_APP_PASSWD="${MARIADB_APP_PASSWD:-}"

install_mariadb() {
  log_info "Installing MariaDB..."

  if systemctl is-active --quiet mariadb 2>/dev/null || systemctl is-active --quiet mysql 2>/dev/null; then
    log_info "MariaDB already running — skipping install"
    mark_service_skipped "mariadb"
    return 0
  fi

  # Pre-flight: free port 3306 if something else is already holding it.
  # apt's post-install script tries to start mariadb immediately; if the port
  # is busy the start fails and dpkg exits with an error code.
  _mariadb_free_port3306

  # Generate passwords if not set
  [[ -z "$MARIADB_ROOT_PASSWD" ]] && MARIADB_ROOT_PASSWD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"
  [[ -z "$MARIADB_APP_PASSWD"  ]] && MARIADB_APP_PASSWD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _install_mariadb_debian
  else
    _install_mariadb_rhel
  fi

  systemctl enable --now mariadb

  _secure_mariadb
  _create_hspanel_db

  log_success "MariaDB installed and configured"
  mark_service_done "mariadb"

  rollback_stop_service "mariadb"
}

# ---------------------------------------------------------------------------
# _mariadb_free_port3306
# ---------------------------------------------------------------------------
# Stop any service that owns port 3306 before MariaDB installation begins.
# The dpkg post-install script starts mariadbd immediately; if port 3306 is
# already bound the daemon exits with status 1 and dpkg returns error code 1.
# ---------------------------------------------------------------------------
_mariadb_free_port3306() {
  # Check if 3306 is in use at all
  if ! ss -tulnp 2>/dev/null | grep -q ':3306'; then
    return 0   # port is free — nothing to do
  fi

  log_warning "[MariaDB] Port 3306 already in use — stopping conflicting service"

  # 1. Try known service names first (clean shutdown)
  for _svc in mysql mysqld mariadb; do
    if systemctl is-active --quiet "$_svc" 2>/dev/null; then
      log_warning "[MariaDB] Stopping ${_svc}.service"
      systemctl stop "$_svc" 2>/dev/null || true
    fi
  done

  # 2. If port is still busy, kill the process holding it directly
  if ss -tulnp 2>/dev/null | grep -q ':3306'; then
    local _pid
    _pid="$(ss -tulnp 2>/dev/null | awk '/:3306 /{match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]; exit}')"
    if [[ -n "$_pid" ]]; then
      log_warning "[MariaDB] Killing PID ${_pid} which holds port 3306"
      kill "$_pid" 2>/dev/null || true
      sleep 2
    fi
  fi

  # 3. Final check — abort early with a clear message rather than letting
  #    dpkg fail with a cryptic error
  if ss -tulnp 2>/dev/null | grep -q ':3306'; then
    log_warning "[MariaDB] Port 3306 still busy after stop attempts — install may fail"
  else
    log_success "[MariaDB] Port 3306 is now free"
  fi
}

_install_mariadb_debian() {
  export DEBIAN_FRONTEND=noninteractive
  # Use MariaDB official repo for consistent version
  curl -fsSL https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | \
    bash -s -- --mariadb-server-version="mariadb-10.11" > /dev/null 2>&1

  apt-get update -qq
  apt-get install -y -qq mariadb-server mariadb-client
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

_secure_mariadb() {
  # Wait for socket
  local retries=10
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
