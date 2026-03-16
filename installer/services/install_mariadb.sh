#!/usr/bin/env bash
# HS-Panel Service Installer - MariaDB
# Installs MariaDB, creates the hspanel database and user.
# Automatically selects an available port (3306, 3307, 3308, ...) if 3306 is busy.

MARIADB_ROOT_PASSWD="${MARIADB_ROOT_PASSWD:-}"
MARIADB_APP_DB="${MARIADB_APP_DB:-hspanel}"
MARIADB_APP_USER="${MARIADB_APP_USER:-hspanel_user}"
MARIADB_APP_PASSWD="${MARIADB_APP_PASSWD:-}"
MARIADB_PORT="${MARIADB_PORT:-3306}"

install_mariadb() {
  log_info "Installing MariaDB..."

  [[ -z "$MARIADB_ROOT_PASSWD" ]] && MARIADB_ROOT_PASSWD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"
  [[ -z "$MARIADB_APP_PASSWD" ]] && MARIADB_APP_PASSWD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"

  _mariadb_pre_install_cleanup

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _install_mariadb_debian
  else
    _install_mariadb_rhel
  fi

  _mariadb_select_port
  _mariadb_configure_port "$MARIADB_PORT"

  mkdir -p /run/mysqld
  chown -R mysql:mysql /run/mysqld 2>/dev/null || true
  chmod 755 /run/mysqld 2>/dev/null || true

  systemctl daemon-reload 2>/dev/null || true
  systemctl enable mariadb 2>/dev/null || true
  systemctl restart mariadb 2>/dev/null || true

  _mariadb_health_check
  _secure_mariadb
  _create_hspanel_db

  log_success "MariaDB installed and configured (port ${MARIADB_PORT})"
  mark_service_done "mariadb"
  rollback_stop_service "mariadb"
}

# Returns 0 if port is free, 1 if busy.
_port_free() {
  local p="$1"

  if ss -tuln 2>/dev/null | awk '{print $5}' | grep -Eq ":${p}$|:${p}[^0-9]"; then
    return 1
  fi

  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${p}" -sTCP:LISTEN -t 2>/dev/null | grep -q .; then
      return 1
    fi
  fi

  return 0
}

# Selects first free port from 3306..3320.
_mariadb_select_port() {
  local candidate=3306

  while (( candidate <= 3320 )); do
    if _port_free "$candidate"; then
      MARIADB_PORT="$candidate"
      export MARIADB_PORT

      if [[ "$candidate" == "3306" ]]; then
        log_info "[HS-Panel] Port 3306 is free"
      else
        log_warning "[HS-Panel] Port 3306 already in use"
        log_info "[HS-Panel] Switching MariaDB to port ${candidate}"
      fi
      return 0
    fi

    log_warning "[HS-Panel] Port ${candidate} is busy - trying next"
    ((candidate++))
  done

  log_error "[HS-Panel] Could not find free MariaDB port in range 3306-3320"
  return 1
}

# Writes selected port into MariaDB server config.
_mariadb_configure_port() {
  local port="$1"
  local cfg="/etc/mysql/mariadb.conf.d/50-server.cnf"

  if [[ ! -f "$cfg" ]]; then
    mkdir -p "$(dirname "$cfg")"
    cat > "$cfg" <<'EOF'
[mysqld]
EOF
  fi

  if ! grep -Eq '^\[mysqld\]' "$cfg"; then
    printf '\n[mysqld]\n' >> "$cfg"
  fi

  if grep -Eq '^[[:space:]]*port[[:space:]]*=' "$cfg"; then
    sed -i -E "s|^[[:space:]]*port[[:space:]]*=.*|port = ${port}|" "$cfg"
  else
    sed -i "/^\[mysqld\]/a port = ${port}" "$cfg"
  fi

  log_info "[HS-Panel] MariaDB configured to listen on port ${port}"
}

_mariadb_pre_install_cleanup() {
  for svc in mysql mysqld mariadb; do
    systemctl stop "$svc" 2>/dev/null || true
  done

  pkill -TERM -f mariadbd 2>/dev/null || true
  pkill -TERM -f mysqld 2>/dev/null || true
  sleep 2
  pkill -KILL -f mariadbd 2>/dev/null || true
  pkill -KILL -f mysqld 2>/dev/null || true
  sleep 1

  local pid=""
  pid="$(ss -tulnp 2>/dev/null | awk '/:3306 /{match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]; exit}' || true)"
  if [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]]; then
    log_warning "[MariaDB] Force-killing PID ${pid} holding port 3306"
    kill -KILL "$pid" 2>/dev/null || true
    sleep 1
  fi

  if [[ "$OS_FAMILY" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get remove --purge -y \
      mariadb-server mariadb-client mariadb-common \
      mysql-server mysql-client mysql-common 2>/dev/null || true
    apt-get autoremove -y 2>/dev/null || true
    rm -f /etc/apt/sources.list.d/mariadb.list.old_* 2>/dev/null || true
    apt-get update -qq 2>/dev/null || true
  fi
}

_install_mariadb_debian() {
  export DEBIAN_FRONTEND=noninteractive
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

_mariadb_health_check() {
  local up=false

  for _i in 1 2 3 4 5 6 7; do
    if ss -tulnp 2>/dev/null | awk '{print $5}' | grep -Eq ":${MARIADB_PORT}$|:${MARIADB_PORT}[^0-9]"; then
      up=true
      break
    fi
    sleep 2
  done

  if $up; then
    log_success "[MariaDB] Listening on port ${MARIADB_PORT}"
    return 0
  fi

  log_error "[MariaDB] Failed to start on port ${MARIADB_PORT}"
  ss -tulnp 2>/dev/null | grep -E ":${MARIADB_PORT}$|:${MARIADB_PORT}[^0-9]" || true
  systemctl status mariadb --no-pager 2>/dev/null || true
  return 1
}

_secure_mariadb() {
  local retries=20
  while (( retries-- > 0 )); do
    mysqladmin --port="${MARIADB_PORT}" ping --silent 2>/dev/null && break || sleep 1
  done

  local auth_mode=""
  if mysql --protocol=socket -u root -e "SELECT 1" >/dev/null 2>&1; then
    auth_mode="socket"
  elif command -v sudo >/dev/null 2>&1 && sudo -n mysql --protocol=socket -u root -e "SELECT 1" >/dev/null 2>&1; then
    auth_mode="sudo-socket"
  elif mysql --port="${MARIADB_PORT}" -u root -e "SELECT 1" >/dev/null 2>&1; then
    auth_mode="tcp"
  elif [[ -f /root/.my.cnf ]] && mysql --defaults-file=/root/.my.cnf --port="${MARIADB_PORT}" -e "SELECT 1" >/dev/null 2>&1; then
    auth_mode="mycnf"
  else
    log_error "[MariaDB] Unable to authenticate as root (socket/tcp) to secure installation"
    return 1
  fi

  if [[ "$auth_mode" == "socket" ]]; then
    mysql --protocol=socket -u root <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASSWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
SQL
  elif [[ "$auth_mode" == "sudo-socket" ]]; then
    sudo mysql --protocol=socket -u root <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASSWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
SQL
  elif [[ "$auth_mode" == "tcp" ]]; then
    mysql --port="${MARIADB_PORT}" -u root <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASSWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
SQL
  else
    mysql --defaults-file=/root/.my.cnf --port="${MARIADB_PORT}" <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASSWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
SQL
  fi

  cat > /root/.my.cnf <<CNF
[client]
user=root
password=${MARIADB_ROOT_PASSWD}
host=127.0.0.1
port=${MARIADB_PORT}
CNF
  chmod 600 /root/.my.cnf
  log_success "MariaDB secured"
}

_create_hspanel_db() {
  mysql --defaults-file=/root/.my.cnf --port="${MARIADB_PORT}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${MARIADB_APP_DB}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MARIADB_APP_USER}'@'localhost'
  IDENTIFIED BY '${MARIADB_APP_PASSWD}';
GRANT ALL PRIVILEGES ON \`${MARIADB_APP_DB}\`.* TO '${MARIADB_APP_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
  log_success "Database '${MARIADB_APP_DB}' and user '${MARIADB_APP_USER}' created"
}
