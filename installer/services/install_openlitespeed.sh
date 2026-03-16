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

  _ols_enable_service
  _ols_start_service

  mark_service_done "openlitespeed"
  rollback_stop_service "openlitespeed"
}

# ---------------------------------------------------------------------------
# _ols_enable_service
# ---------------------------------------------------------------------------
# systemctl enable fails with "Refusing to operate on alias name or linked
# unit file" when OLS is installed from the official LiteSpeed apt/yum repo,
# because both lsws.service and openlitespeed.service are aliases for a
# systemd-generated wrapper around the /etc/init.d/lsws SysV script.
#
# Strategy (tried in order):
#   1. Enable by FragmentPath (absolute path avoids alias resolution).
#   2. update-rc.d  — Debian / Ubuntu with SysV init script.
#   3. chkconfig    — RHEL / AlmaLinux.
#   4. Warn and continue — don't abort the install for a boot-time flag.
# ---------------------------------------------------------------------------
_ols_enable_service() {
  local enabled=false

  # 1. Try enabling by the real file path (skips alias check)
  local fragment
  fragment="$(systemctl show -p FragmentPath openlitespeed.service 2>/dev/null \
    | cut -d= -f2 || true)"
  if [[ -n "$fragment" && -f "$fragment" && "$fragment" != /run/systemd/* ]]; then
    if systemctl enable "$fragment" 2>/dev/null; then
      enabled=true
      log_success "OpenLiteSpeed service enabled"
    fi
  fi

  # 2. init.d + update-rc.d (Debian/Ubuntu — official LiteSpeed repo installs
  #    /etc/init.d/lsws and systemd generates a transient wrapper that cannot
  #    be enabled via systemctl enable)
  if ! $enabled && [[ -f /etc/init.d/lsws ]] && command -v update-rc.d &>/dev/null; then
    update-rc.d lsws defaults 2>/dev/null || true
    update-rc.d lsws enable  2>/dev/null || true
    enabled=true
    log_success "OpenLiteSpeed service enabled (via update-rc.d)"
  fi

  # 3. chkconfig — RHEL / AlmaLinux
  if ! $enabled && command -v chkconfig &>/dev/null; then
    chkconfig lsws on 2>/dev/null || true
    enabled=true
    log_success "OpenLiteSpeed service enabled (via chkconfig)"
  fi

  if ! $enabled; then
    log_warning "[OpenLiteSpeed] Could not enable service at boot — will start manually"
  fi
}

# ---------------------------------------------------------------------------
# _ols_start_service — start OLS with layered fallbacks
# ---------------------------------------------------------------------------
_ols_start_service() {
  # Try systemctl start (works even when enable is the one that fails)
  if ! systemctl start openlitespeed 2>/dev/null; then
    log_warning "[OpenLiteSpeed] systemd start failed — trying init.d script"
    if [[ -f /etc/init.d/lsws ]]; then
      /etc/init.d/lsws start 2>/dev/null || true
    else
      /usr/local/lsws/bin/lswsctrl start 2>/dev/null || true
    fi
  fi

  # Give OLS a moment to fully bind its ports (OLS admin UI takes ~5 s)
  sleep 6

  # Verify process is up
  if systemctl is-active --quiet openlitespeed 2>/dev/null || \
     pgrep -x litespeed &>/dev/null; then
    log_success "OpenLiteSpeed running"
  else
    echo "[ERROR] OpenLiteSpeed failed to start"
    systemctl status openlitespeed --no-pager 2>/dev/null || true
    return 1
  fi

  # Verify admin port 8090 is listening
  if ss -tulnp 2>/dev/null | grep -q ':8090'; then
    log_success "OpenLiteSpeed running on port 8090"
  else
    log_warning "[OpenLiteSpeed] port 8090 not yet listening — OLS may still be initialising"
  fi
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
