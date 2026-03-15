#!/usr/bin/env bash
# HS-Panel Service Installer — PowerDNS
# Installs PowerDNS with MySQL backend for DNS zone management.

PDNS_DB="${PDNS_DB:-pdns}"
PDNS_DB_USER="${PDNS_DB_USER:-pdns}"
PDNS_DB_PASSWD="${PDNS_DB_PASSWD:-}"
PDNS_API_KEY="${PDNS_API_KEY:-}"
PDNS_API_PORT="${PDNS_API_PORT:-8053}"

install_powerdns() {
  log_info "Installing PowerDNS..."

  if systemctl is-active --quiet pdns 2>/dev/null || systemctl is-active --quiet pdns.service 2>/dev/null; then
    log_info "PowerDNS already running — skipping"
    mark_service_skipped "powerdns"
    return 0
  fi

  [[ -z "$PDNS_DB_PASSWD" ]] && PDNS_DB_PASSWD="$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 18)"
  [[ -z "$PDNS_API_KEY"   ]] && PDNS_API_KEY="$(openssl rand -hex 16)"

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _install_pdns_debian
  else
    _install_pdns_rhel
  fi

  _create_pdns_db
  _configure_pdns
  systemctl enable --now pdns

  log_success "PowerDNS installed (API port: $PDNS_API_PORT)"
  mark_service_done "powerdns"
  rollback_stop_service "pdns"
}

_install_pdns_debian() {
  export DEBIAN_FRONTEND=noninteractive

  # Use PowerDNS official repo
  install -d /etc/apt/keyrings
  curl -fsSL https://repo.powerdns.com/FD380FBB-pub.asc \
    -o /etc/apt/keyrings/pdns.asc 2>/dev/null || true

  local codename="${OS_CODENAME:-$(lsb_release -cs 2>/dev/null)}"
  cat > /etc/apt/sources.list.d/powerdns.list <<SOURCES
# PowerDNS repository
deb [signed-by=/etc/apt/keyrings/pdns.asc] http://repo.powerdns.com/debian ${codename}-auth-48 main
SOURCES

  cat > /etc/apt/preferences.d/pdns <<PREF
Package: pdns-*
Pin: origin repo.powerdns.com
Pin-Priority: 600
PREF

  apt-get update -qq 2>/dev/null || true
  apt-get install -y -qq pdns-server pdns-backend-mysql 2>/dev/null || \
    apt-get install -y -qq pdns-server pdns-backend-mysql || \
    { log_warning "PowerDNS from official repo failed; falling back to distro packages..."; \
      apt-get install -y -qq pdns-server pdns-backend-mysql; }
}

_install_pdns_rhel() {
  curl -o /etc/yum.repos.d/powerdns.repo \
    "https://repo.powerdns.com/rpm/rhel-auth-48.repo" 2>/dev/null || true
  dnf install -y pdns pdns-backend-mysql --skip-broken || \
    dnf install -y pdns pdns-backend-mysql
}

_create_pdns_db() {
  mysql --defaults-file=/root/.my.cnf <<SQL
CREATE DATABASE IF NOT EXISTS \`${PDNS_DB}\` CHARACTER SET utf8;
CREATE USER IF NOT EXISTS '${PDNS_DB_USER}'@'localhost' IDENTIFIED BY '${PDNS_DB_PASSWD}';
GRANT ALL PRIVILEGES ON \`${PDNS_DB}\`.* TO '${PDNS_DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

  # Import PowerDNS schema
  local schema_paths=(
    /usr/share/doc/pdns-backend-mysql/schema.mysql.sql
    /usr/share/doc/pdns-backend-mysql/schema.mysql.sql.gz
    /usr/share/pdns-backend-mysql/schema.mysql.sql
  )
  for path in "${schema_paths[@]}"; do
    if [[ -f "$path" ]]; then
      if [[ "$path" == *.gz ]]; then
        zcat "$path" | mysql --defaults-file=/root/.my.cnf "$PDNS_DB"
      else
        mysql --defaults-file=/root/.my.cnf "$PDNS_DB" < "$path"
      fi
      log_info "PowerDNS schema imported from $path"
      return 0
    fi
  done

  # Inline schema fallback
  mysql --defaults-file=/root/.my.cnf "$PDNS_DB" <<'SCHEMA'
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
  log_info "PowerDNS schema created (inline fallback)"
}

_configure_pdns() {
  cat > /etc/powerdns/pdns.conf <<CONF
# HS-Panel PowerDNS configuration
local-address=0.0.0.0
local-port=53
daemon=yes
guardian=yes
setuid=pdns
setgid=pdns

launch=gmysql
gmysql-host=127.0.0.1
gmysql-port=3306
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
