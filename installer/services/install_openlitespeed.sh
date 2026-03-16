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
# _ols_resolve_unit
# ---------------------------------------------------------------------------
# The real systemd unit name varies by OLS version and install method:
#   lshttpd.service     — current official LiteSpeed apt/yum packages
#   openlitespeed.service — older packages / some distros
#   lsws.service        — SysV-generated wrapper (alias, cannot be enabled)
# Returns the first unit name found in the systemd unit list.
# ---------------------------------------------------------------------------
_ols_resolve_unit() {
  for _u in lshttpd openlitespeed lsws; do
    if systemctl list-unit-files --type=service 2>/dev/null \
        | grep -q "^${_u}\.service"; then
      echo "$_u"
      return
    fi
  done
  echo ""
}

# Populated by _ols_enable_service, consumed by _ols_start_service
OLS_SVC_UNIT=""

# ---------------------------------------------------------------------------
# _ols_enable_service
# ---------------------------------------------------------------------------
# Strategy (tried in order):
#   1. systemctl enable <resolved-unit>  — works for lshttpd.service
#   2. Enable by FragmentPath            — bypasses alias check
#   3. update-rc.d                       — Debian/Ubuntu SysV path
#   4. chkconfig                         — RHEL/AlmaLinux
#   5. Warn and continue                 — don't abort for a boot flag
# ---------------------------------------------------------------------------
_ols_enable_service() {
  OLS_SVC_UNIT="$(_ols_resolve_unit)"
  local enabled=false

  # 1. Enable by resolved unit name (covers lshttpd.service)
  if [[ -n "$OLS_SVC_UNIT" ]]; then
    if systemctl enable "$OLS_SVC_UNIT" 2>/dev/null; then
      enabled=true
      log_success "OpenLiteSpeed service enabled"
    fi
  fi

  # 2. Enable by FragmentPath (bypasses alias resolution for edge cases)
  if ! $enabled && [[ -n "$OLS_SVC_UNIT" ]]; then
    local fragment
    fragment="$(systemctl show -p FragmentPath "${OLS_SVC_UNIT}.service" 2>/dev/null \
      | cut -d= -f2 || true)"
    if [[ -n "$fragment" && -f "$fragment" && "$fragment" != /run/systemd/* ]]; then
      if systemctl enable "$fragment" 2>/dev/null; then
        enabled=true
        log_success "OpenLiteSpeed service enabled"
      fi
    fi
  fi

  # 3. update-rc.d — Debian/Ubuntu with SysV init script
  if ! $enabled && [[ -f /etc/init.d/lsws ]] && command -v update-rc.d &>/dev/null; then
    update-rc.d lsws defaults 2>/dev/null || true
    update-rc.d lsws enable  2>/dev/null || true
    enabled=true
    log_success "OpenLiteSpeed service enabled (via update-rc.d)"
  fi

  # 4. chkconfig — RHEL/AlmaLinux
  if ! $enabled && command -v chkconfig &>/dev/null; then
    chkconfig lsws on 2>/dev/null || true
    enabled=true
    log_success "OpenLiteSpeed service enabled (via chkconfig)"
  fi

  if ! $enabled; then
    log_warning "[OpenLiteSpeed] Could not enable at boot — will start manually"
  fi
}

# ---------------------------------------------------------------------------
# _ols_start_service — start OLS with pre-flight and layered fallbacks
# ---------------------------------------------------------------------------
_ols_start_service() {
  OLS_SVC_UNIT="${OLS_SVC_UNIT:-$(_ols_resolve_unit)}"

  # Pre-flight: stop any service holding port 80 so OLS can bind
  for _blocker in apache2 nginx httpd; do
    if systemctl is-active --quiet "$_blocker" 2>/dev/null; then
      log_warning "[OpenLiteSpeed] Stopping ${_blocker} to free port 80"
      systemctl stop "$_blocker" 2>/dev/null || true
    fi
  done

  # Start via lswsctrl directly — this is exactly what the unit's ExecStart
  # calls, and it avoids all unit-name / alias confusion entirely.
  if [[ -x /usr/local/lsws/bin/lswsctrl ]]; then
    /usr/local/lsws/bin/lswsctrl start 2>/dev/null || true
  elif [[ -n "$OLS_SVC_UNIT" ]]; then
    systemctl start "$OLS_SVC_UNIT" 2>/dev/null || true
  elif [[ -f /etc/init.d/lsws ]]; then
    /etc/init.d/lsws start 2>/dev/null || true
  fi

  # Give OLS time to fully initialise and bind ports
  sleep 6

  # Verify: lswsctrl status is the most reliable check regardless of
  # how the process was started or what the unit name is
  local is_running=false
  if /usr/local/lsws/bin/lswsctrl status 2>/dev/null | grep -qi "running"; then
    is_running=true
  elif pgrep -f "/usr/local/lsws" &>/dev/null; then
    is_running=true
  elif [[ -n "$OLS_SVC_UNIT" ]] && systemctl is-active --quiet "$OLS_SVC_UNIT" 2>/dev/null; then
    is_running=true
  fi

  if $is_running; then
    log_success "OpenLiteSpeed running"
  else
    echo "[ERROR] OpenLiteSpeed failed to start"
    if [[ -n "$OLS_SVC_UNIT" ]]; then
      systemctl status "$OLS_SVC_UNIT" --no-pager 2>/dev/null || true
    fi
    # Show OLS own error log for diagnostics
    if [[ -f /usr/local/lsws/logs/error.log ]]; then
      echo "--- OLS error log (last 20 lines) ---"
      tail -20 /usr/local/lsws/logs/error.log 2>/dev/null || true
    fi
    return 1
  fi

  # Verify admin port 8090 is listening
  if ss -tulnp 2>/dev/null | grep -q ':8090'; then
    log_success "OpenLiteSpeed running on port 8090"
  else
    log_warning "[OpenLiteSpeed] port 8090 not yet listening — check /usr/local/lsws/logs/error.log"
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
