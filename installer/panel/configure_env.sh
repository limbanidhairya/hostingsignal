#!/usr/bin/env bash
# HS-Panel Installer — Environment Configuration

HSPANEL_INSTALL_DIR="${HSPANEL_INSTALL_DIR:-/opt/hostingsignal}"
HSPANEL_ENV_FILE="${HSPANEL_ENV_FILE:-/opt/hostingsignal/deployment/hostingsignal-devapi.production.env}"
HSPANEL_CREDS_FILE="${HSPANEL_CREDS_FILE:-/root/hspanel_credentials.txt}"

_is_private_ipv4() {
  local ip="$1"
  [[ "$ip" =~ ^10\. ]] || [[ "$ip" =~ ^192\.168\. ]] || [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]]
}

_detect_network_info() {
  local all_ipv4 private_ip first_ip public_ip
  all_ipv4="$(ip -4 addr show up scope global 2>/dev/null | awk '/inet /{split($2,a,"/"); print a[1]}' || true)"
  private_ip="$(printf '%s\n' "$all_ipv4" | awk '/^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)/{print; exit}' || true)"
  first_ip="$(printf '%s\n' "$all_ipv4" | awk 'NF{print; exit}' || true)"
  public_ip="$(curl -fsSL --max-time 5 https://api.ipify.org 2>/dev/null || true)"

  if [[ -n "$public_ip" ]] && _is_private_ipv4 "$public_ip"; then
    public_ip=""
  fi

  export HSPANEL_PRIVATE_IP="${private_ip:-${first_ip:-127.0.0.1}}"
  export HSPANEL_PUBLIC_IP="${public_ip:-}"
}

configure_env() {
  log_info "Generating production environment configuration..."

  mkdir -p "$(dirname "$HSPANEL_ENV_FILE")"
  chmod 700 "$(dirname "$HSPANEL_ENV_FILE")"

  _detect_network_info

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
WEB_PORT=3001
HOST=0.0.0.0
API_HOST=0.0.0.0
WEB_HOST=0.0.0.0

DB_HOST=127.0.0.1
DB_PORT=${MARIADB_PORT:-3306}
DB_NAME=${MARIADB_APP_DB:-hspanel}
DB_USER=${MARIADB_APP_USER:-hspanel_user}
DB_PASSWORD=${MARIADB_APP_PASSWD:-}
DATABASE_URL=mysql+aiomysql://${MARIADB_APP_USER:-hspanel_user}:${MARIADB_APP_PASSWD:-}@127.0.0.1:${MARIADB_PORT:-3306}/${MARIADB_APP_DB:-hspanel}
HSDEV_DATABASE_URL=mysql+aiomysql://${MARIADB_APP_USER:-hspanel_user}:${MARIADB_APP_PASSWD:-}@127.0.0.1:${MARIADB_PORT:-3306}/${MARIADB_APP_DB:-hspanel}
HSDEV_HOST=0.0.0.0
HSDEV_PORT=3000

JWT_SECRET_KEY=${jwt_secret}
LICENSE_API_KEY=${license_key}
HSDEV_JWT_SECRET=${jwt_secret}

PANEL_ADMIN_USERNAME=${HSPANEL_ADMIN_USER:-admin}
PANEL_ADMIN_PASSWORD=${HSPANEL_ADMIN_PASSWD:-}
HSDEV_DEFAULT_ADMIN_USERNAME=${HSPANEL_ADMIN_USER:-admin}
HSDEV_DEFAULT_ADMIN_PASSWORD=${HSPANEL_ADMIN_PASSWD:-}
HSDEV_DEFAULT_ADMIN_EMAIL=${HSPANEL_ADMIN_EMAIL:-admin@hostingsignal.local}
HSDEV_DEFAULT_ADMIN_LOGIN=${HSPANEL_ADMIN_USER:-admin}

PANEL_PUBLIC_URL=http://localhost:2086
PANEL_PUBLIC_SSL_URL=https://localhost:2087
API_PUBLIC_URL=http://localhost:3000
HSDEV_INTERNAL_API_BASE=http://127.0.0.1:3000
NEXT_PUBLIC_HSDEV_API_BASE=/devapi

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

  _write_credentials_file
}

_write_credentials_file() {
  cat > "$HSPANEL_CREDS_FILE" <<CREDS
HostingSignal HS-Panel Installation Credentials
Generated: $(date)

Detected Network:
Private IP:       ${HSPANEL_PRIVATE_IP:-127.0.0.1}
Public IP:        ${HSPANEL_PUBLIC_IP:-Not reachable}

HS-Panel Access:
Local Access:     http://localhost:2086/login
LAN Access:       http://${HSPANEL_PRIVATE_IP:-127.0.0.1}:2086/login
LAN HTTPS:        https://${HSPANEL_PRIVATE_IP:-127.0.0.1}:2087
API Health:       http://localhost:3000/health
OpenLiteSpeed:    http://localhost:${OLS_ADMIN_PORT:-8090}
phpMyAdmin:       http://${HSPANEL_PRIVATE_IP:-127.0.0.1}/phpmyadmin
Webmail:          http://${HSPANEL_PRIVATE_IP:-127.0.0.1}/webmail
Public Access:    ${HSPANEL_PUBLIC_IP:+http://${HSPANEL_PUBLIC_IP}:2086/login}

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
