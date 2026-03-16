#!/usr/bin/env bash
# HS-Panel Service Installer — OpenLiteSpeed
# Installs and configures OpenLiteSpeed web server.

OLS_ADMIN_PORT="${OLS_ADMIN_PORT:-8090}"
OLS_ADMIN_USER="${OLS_ADMIN_USER:-admin}"
OLS_ADMIN_PASSWD="${OLS_ADMIN_PASSWD:-}"  # set before calling install_openlitespeed
OLS_VHOST_ROOT="${OLS_VHOST_ROOT:-/var/www}"

install_openlitespeed() {
  log_info "Installing OpenLiteSpeed..."

  if command -v lswsctrl &>/dev/null && lswsctrl status 2>/dev/null | grep -q "litespeed is running"; then
    log_info "OpenLiteSpeed already running — skipping install"
    mark_service_skipped "openlitespeed"
    return 0
  fi

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _install_ols_debian
  else
    _install_ols_rhel
  fi

  _configure_ols_admin
  _configure_ols_default_vhost

  # Enable the real unit (lsws.service is only an alias and cannot be enabled)
  systemctl enable openlitespeed
  log_success "OpenLiteSpeed service enabled"

  # Start the service
  systemctl start openlitespeed

  # Verify the service came up; fall back to the binary controller if systemd fails
  if ! systemctl is-active --quiet openlitespeed; then
    log_warning "[OpenLiteSpeed] systemd start failed — attempting manual start via lswsctrl"
    /usr/local/lsws/bin/lswsctrl start 2>/dev/null || true
    sleep 2
    if ! systemctl is-active --quiet openlitespeed; then
      echo "[ERROR] OpenLiteSpeed failed to start"
      systemctl status openlitespeed --no-pager 2>/dev/null || true
      return 1
    fi
  fi
  log_success "OpenLiteSpeed running"

  # Verify admin port 8090 is listening
  if ss -tulnp 2>/dev/null | grep -q ':8090'; then
    log_success "OpenLiteSpeed running on port 8090"
  else
    log_warning "[OpenLiteSpeed] port 8090 not yet listening — OLS may still be initialising"
  fi

  mark_service_done "openlitespeed"

  rollback_stop_service "openlitespeed"
}

_install_ols_debian() {
  # Add OpenLiteSpeed repository
  wget -qO /tmp/ols.key "https://repo.litespeed.sh" 2>/dev/null
  bash /tmp/ols.key > /dev/null 2>&1

  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq openlitespeed
}

_install_ols_rhel() {
  rpm --import "https://repo.litespeed.sh" 2>/dev/null || true
  dnf install -y "https://repo.litespeed.sh/litespeed.repo" 2>/dev/null || \
    curl -fsSL "https://repo.litespeed.sh" | bash > /dev/null 2>&1
  dnf install -y openlitespeed --skip-broken
}

_configure_ols_admin() {
  local passwd_file="/usr/local/lsws/admin/conf/htpasswd"

  # Generate password if not set
  if [[ -z "$OLS_ADMIN_PASSWD" ]]; then
    OLS_ADMIN_PASSWD="$(openssl rand -base64 16 | tr -dc 'A-Za-z0-9' | head -c 16)"
  fi

  # Write admin credentials
  mkdir -p "$(dirname "$passwd_file")"
  if command -v /usr/local/lsws/admin/fcgi-bin/admin_php &>/dev/null; then
    echo "$OLS_ADMIN_PASSWD" | /usr/local/lsws/admin/fcgi-bin/admin_php -q \
      /usr/local/lsws/admin/misc/htpasswd.php "$passwd_file" "$OLS_ADMIN_USER" 2>/dev/null || true
  else
    # Fallback: generate htpasswd entry
    if command -v htpasswd &>/dev/null; then
      htpasswd -b -c "$passwd_file" "$OLS_ADMIN_USER" "$OLS_ADMIN_PASSWD"
    else
      local hash
      hash="$(openssl passwd -apr1 "$OLS_ADMIN_PASSWD")"
      echo "${OLS_ADMIN_USER}:${hash}" > "$passwd_file"
    fi
  fi

  chmod 600 "$passwd_file" 2>/dev/null || true
  log_kv "OLS Admin User"  "$OLS_ADMIN_USER"
  log_kv "OLS Admin Port"  "$OLS_ADMIN_PORT"
}

_configure_ols_default_vhost() {
  mkdir -p "$OLS_VHOST_ROOT/hspanel/html"
  cat > "$OLS_VHOST_ROOT/hspanel/html/index.html" <<'EOF'
<!DOCTYPE html>
<html>
<head><title>HostingSignal Panel</title></head>
<body><h1>HostingSignal Panel — Web Server Ready</h1></body>
</html>
EOF
}
