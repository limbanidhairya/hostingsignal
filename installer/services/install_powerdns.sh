#!/usr/bin/env bash
# HS-Panel Service Installer — PowerDNS
# Installs PowerDNS with MySQL backend for DNS zone management.

PDNS_DB="${PDNS_DB:-pdns}"
PDNS_DB_USER="${PDNS_DB_USER:-pdns}"
PDNS_DB_PASSWD="${PDNS_DB_PASSWD:-}"
PDNS_API_KEY="${PDNS_API_KEY:-}"
PDNS_API_PORT="${PDNS_API_PORT:-8053}"
PDNS_DB_PORT="${PDNS_DB_PORT:-}"
PDNS_LOCAL_PORT="${PDNS_LOCAL_PORT:-}"

install_powerdns() {
  log_info "Installing PowerDNS..."

  if systemctl is-active --quiet pdns 2>/dev/null || systemctl is-active --quiet pdns.service 2>/dev/null; then
    log_info "PowerDNS already running — skipping"
    mark_service_skipped "powerdns"
    return 0
  fi

  [[ -z "$PDNS_DB_PASSWD" ]] && PDNS_DB_PASSWD="$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 18)"
  [[ -z "$PDNS_API_KEY"   ]] && PDNS_API_KEY="$(openssl rand -hex 16)"

  _resolve_pdns_db_port
  _resolve_pdns_local_port

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _install_pdns_debian
  else
    _install_pdns_rhel
  fi

  _create_pdns_db
  _configure_pdns
  if ! systemctl enable --now pdns; then
    log_error "PowerDNS failed to start"
    systemctl status pdns --no-pager 2>/dev/null || true
    journalctl -xeu pdns.service --no-pager -n 80 2>/dev/null || true
    return 1
  fi

  log_success "PowerDNS installed (DNS port: $PDNS_LOCAL_PORT, API port: $PDNS_API_PORT)"
  mark_service_done "powerdns"
  rollback_stop_service "pdns"
}

_resolve_pdns_db_port() {
  if [[ -z "${PDNS_DB_PORT}" ]]; then
    if [[ -n "${MARIADB_PORT:-}" ]]; then
      PDNS_DB_PORT="${MARIADB_PORT}"
    elif [[ -f /root/.my.cnf ]]; then
      PDNS_DB_PORT="$(awk -F= '/^[[:space:]]*port[[:space:]]*=/{gsub(/[[:space:]]/,"",$2); print $2; exit}' /root/.my.cnf 2>/dev/null || true)"
    elif [[ -f /etc/mysql/mariadb.conf.d/50-server.cnf ]]; then
      PDNS_DB_PORT="$(awk -F= '/^[[:space:]]*port[[:space:]]*=/{gsub(/[[:space:]]/,"",$2); print $2; exit}' /etc/mysql/mariadb.conf.d/50-server.cnf 2>/dev/null || true)"
    fi
  fi

  [[ -z "${PDNS_DB_PORT}" ]] && PDNS_DB_PORT="3306"
  log_info "[PowerDNS] Using MariaDB port ${PDNS_DB_PORT}"
}

_resolve_pdns_local_port() {
  if [[ -n "${PDNS_LOCAL_PORT}" ]]; then
    log_info "[PowerDNS] Using configured DNS port ${PDNS_LOCAL_PORT}"
    return 0
  fi

  if ss -tuln 2>/dev/null | awk '{print $5}' | grep -Eq ':53$|:53[^0-9]'; then
    PDNS_LOCAL_PORT="5300"
    log_warning "[PowerDNS] Port 53 busy; switching DNS listener to ${PDNS_LOCAL_PORT}"
  else
    PDNS_LOCAL_PORT="53"
    log_info "[PowerDNS] Port 53 is free"
  fi
}

_install_pdns_debian() {
  export DEBIAN_FRONTEND=noninteractive

  # Remove stale/invalid PowerDNS repo entries from earlier runs.
  rm -f /etc/apt/sources.list.d/powerdns.list 2>/dev/null || true
  rm -f /etc/apt/preferences.d/pdns 2>/dev/null || true

  # Prefer distro packages for reliability across Ubuntu/Debian releases.
  apt-get update -qq
  apt-get install -y -qq pdns-server pdns-backend-mysql
}

_install_pdns_rhel() {
  curl -o /etc/yum.repos.d/powerdns.repo \
    "https://repo.powerdns.com/rpm/rhel-auth-48.repo" 2>/dev/null || true
  dnf install -y pdns pdns-backend-mysql --skip-broken || \
    dnf install -y pdns pdns-backend-mysql
}

_create_pdns_db() {
  mysql --defaults-file=/root/.my.cnf --port="${PDNS_DB_PORT}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${PDNS_DB}\` CHARACTER SET utf8;
CREATE USER IF NOT EXISTS '${PDNS_DB_USER}'@'localhost' IDENTIFIED BY '${PDNS_DB_PASSWD}';
CREATE USER IF NOT EXISTS '${PDNS_DB_USER}'@'127.0.0.1' IDENTIFIED BY '${PDNS_DB_PASSWD}';
GRANT ALL PRIVILEGES ON \`${PDNS_DB}\`.* TO '${PDNS_DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${PDNS_DB}\`.* TO '${PDNS_DB_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

  # Idempotency guard: if schema already exists, skip import safely.
  if mysql --defaults-file=/root/.my.cnf --port="${PDNS_DB_PORT}" -Nse "SHOW TABLES IN \`${PDNS_DB}\` LIKE 'domains';" 2>/dev/null | grep -qx 'domains'; then
    log_info "[HS-Panel] PowerDNS schema already exists - skipping schema import"
    return 0
  fi

  # Import PowerDNS schema
  local schema_paths=(
    /usr/share/doc/pdns-backend-mysql/schema.mysql.sql
    /usr/share/doc/pdns-backend-mysql/schema.mysql.sql.gz
    /usr/share/pdns-backend-mysql/schema.mysql.sql
  )
  for path in "${schema_paths[@]}"; do
    if [[ -f "$path" ]]; then
      if [[ "$path" == *.gz ]]; then
        if zcat "$path" | mysql --defaults-file=/root/.my.cnf --port="${PDNS_DB_PORT}" "$PDNS_DB"; then
          log_info "PowerDNS schema imported from $path"
          return 0
        fi
      else
        if mysql --defaults-file=/root/.my.cnf --port="${PDNS_DB_PORT}" "$PDNS_DB" < "$path"; then
          log_info "PowerDNS schema imported from $path"
          return 0
        fi
      fi
      log_warning "PowerDNS schema import failed from $path, trying next option"
    fi
  done

  # Inline schema fallback
  mysql --defaults-file=/root/.my.cnf --port="${PDNS_DB_PORT}" "$PDNS_DB" <<'SCHEMA'
CREATE TABLE IF NOT EXISTS domains (
  id INT AUTO_INCREMENT NOT NULL, name VARCHAR(255) NOT NULL, master VARCHAR(128) DEFAULT NULL,
  last_check INT DEFAULT NULL, type VARCHAR(6) NOT NULL, notified_serial INT UNSIGNED DEFAULT NULL,
  account VARCHAR(40) CHARACTER SET 'utf8' DEFAULT NULL, PRIMARY KEY (id)
) Engine=InnoDB CHARACTER SET 'latin1';
CREATE UNIQUE INDEX name_index ON domains(name);

CREATE TABLE IF NOT EXISTS records (
  id BIGINT AUTO_INCREMENT NOT NULL, domain_id INT DEFAULT NULL,
  name VARCHAR(255) DEFAULT NULL, type VARCHAR(10) DEFAULT NULL,
  content VARCHAR(64000) DEFAULT NULL, ttl INT DEFAULT NULL,
  prio INT DEFAULT NULL, disabled TINYINT(1) DEFAULT 0,
  ordername VARCHAR(255) BINARY DEFAULT NULL, auth TINYINT(1) DEFAULT 1,
  PRIMARY KEY (id)
) Engine=InnoDB CHARACTER SET 'latin1';
CREATE INDEX nametype_index ON records(name,type);
CREATE INDEX domain_id ON records(domain_id);
SCHEMA

  if mysql --defaults-file=/root/.my.cnf --port="${PDNS_DB_PORT}" -Nse "SHOW TABLES IN \`${PDNS_DB}\` LIKE 'domains';" 2>/dev/null | grep -qx 'domains'; then
    log_info "PowerDNS schema created (inline fallback)"
    return 0
  fi

  log_error "[HS-Panel] PowerDNS schema import failed and domains table is still missing"
  return 1
}

_configure_pdns() {
  cat > /etc/powerdns/pdns.conf <<CONF
# HS-Panel PowerDNS configuration
local-address=0.0.0.0
local-port=${PDNS_LOCAL_PORT}
daemon=no
guardian=no
setuid=pdns
setgid=pdns

launch=gmysql
gmysql-host=127.0.0.1
gmysql-port=${PDNS_DB_PORT}
gmysql-dbname=${PDNS_DB}
gmysql-user=${PDNS_DB_USER}
gmysql-password=${PDNS_DB_PASSWD}

api=yes
api-key=${PDNS_API_KEY}
webserver=yes
webserver-address=127.0.0.1
webserver-port=${PDNS_API_PORT}
webserver-allow-from=127.0.0.1,::1

default-ttl=3600
CONF
  chmod 640 /etc/powerdns/pdns.conf
}
