#!/usr/bin/env bash
# HS-Panel Installer — Environment Configuration

HSPANEL_INSTALL_DIR="${HSPANEL_INSTALL_DIR:-/opt/hostingsignal}"
HSPANEL_ENV_FILE="${HSPANEL_ENV_FILE:-/opt/hostingsignal/deployment/hostingsignal-devapi.production.env}"
HSPANEL_CREDS_FILE="${HSPANEL_CREDS_FILE:-/root/hspanel_credentials.txt}"

configure_env() {
  log_info "Generating production environment configuration..."

  mkdir -p "$(dirname "$HSPANEL_ENV_FILE")"
  chmod 700 "$(dirname "$HSPANEL_ENV_FILE")"

  local server_ip
  server_ip="$(curl -fsSL --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}' || echo "127.0.0.1")"

  local jwt_secret
  local license_key
  jwt_secret="$(openssl rand -hex 32)"
  license_key="$(openssl rand -hex 20)"

  cat > "$HSPANEL_ENV_FILE" <<ENV
# HostingSignal HS-Panel Production Environment
# Generated on $(date)

PANEL_PORT=2086
PANEL_SSL_PORT=2087
API_PORT=3000

DB_HOST=localhost
DB_PORT=3306
DB_NAME=${MARIADB_APP_DB:-hspanel}
DB_USER=${MARIADB_APP_USER:-hspanel_user}
DB_PASSWORD=${MARIADB_APP_PASSWD:-}
DATABASE_URL=mysql+pymysql://${MARIADB_APP_USER:-hspanel_user}:${MARIADB_APP_PASSWD:-}@localhost:3306/${MARIADB_APP_DB:-hspanel}

JWT_SECRET_KEY=${jwt_secret}
LICENSE_API_KEY=${license_key}

PANEL_ADMIN_USERNAME=${HSPANEL_ADMIN_USER:-admin}
PANEL_ADMIN_PASSWORD=${HSPANEL_ADMIN_PASSWD:-}

PANEL_PUBLIC_URL=http://${server_ip}:2086
PANEL_PUBLIC_SSL_URL=https://${server_ip}:2087
API_PUBLIC_URL=http://${server_ip}:3000

PDNS_API_URL=http://127.0.0.1:${PDNS_API_PORT:-8053}/api/v1
PDNS_API_KEY=${PDNS_API_KEY:-}

MAIL_DOMAIN=${MAIL_DOMAIN:-localdomain}

DEFAULT_DISK_QUOTA_MB=5120
DEFAULT_DOMAIN_LIMIT=10
DEFAULT_EMAIL_LIMIT=50
DEFAULT_DATABASE_LIMIT=20
ENV

  chmod 640 "$HSPANEL_ENV_FILE"
  log_success "Environment file written: $HSPANEL_ENV_FILE"

  _write_credentials_file "$server_ip"
}

_write_credentials_file() {
  local server_ip="$1"

  cat > "$HSPANEL_CREDS_FILE" <<CREDS
HostingSignal HS-Panel Installation Credentials
Generated: $(date)

Panel URL:        http://${server_ip}:2086
Panel HTTPS:      https://${server_ip}:2087
API:              http://${server_ip}:3000
OpenLiteSpeed:    http://${server_ip}:${OLS_ADMIN_PORT:-8090}
phpMyAdmin:       http://${server_ip}/phpmyadmin
Webmail:          http://${server_ip}/webmail

Admin Username:   ${HSPANEL_ADMIN_USER:-admin}
Admin Password:   ${HSPANEL_ADMIN_PASSWD:-}

Database Name:    ${MARIADB_APP_DB:-hspanel}
Database User:    ${MARIADB_APP_USER:-hspanel_user}
Database Pass:    ${MARIADB_APP_PASSWD:-}
DB Root Pass:     ${MARIADB_ROOT_PASSWD:-}

PowerDNS API Key: ${PDNS_API_KEY:-}

Panel Path:       ${HSPANEL_INSTALL_DIR}
Env File:         ${HSPANEL_ENV_FILE}
Install Log:      /var/log/hspanel_install.log
CREDS

  chmod 600 "$HSPANEL_CREDS_FILE"
  log_success "Credentials saved: $HSPANEL_CREDS_FILE"
}
