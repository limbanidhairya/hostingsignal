#!/usr/bin/env bash
# HS-Panel Health Check — Web Server (OpenLiteSpeed)

check_webserver() {
  local status=0

  # 1. Process check
  if pgrep -x "litespeed" >/dev/null 2>&1; then
    log_success "  [webserver] litespeed process running"
  else
    log_error   "  [webserver] litespeed process NOT found"
    status=1
  fi

  # 2. Systemd unit check — probe the real unit name (lshttpd, openlitespeed, or lsws)
  local _ols_unit=""
  for _u in lshttpd openlitespeed lsws; do
    if systemctl list-unit-files --type=service 2>/dev/null | grep -q "^${_u}\.service"; then
      _ols_unit="$_u"; break
    fi
  done
  if [[ -n "$_ols_unit" ]] && systemctl is-active --quiet "$_ols_unit" 2>/dev/null; then
    log_success "  [webserver] systemd unit ${_ols_unit}.service is active"
  elif /usr/local/lsws/bin/lswsctrl status 2>/dev/null | grep -qi "running"; then
    log_success "  [webserver] OpenLiteSpeed running (via lswsctrl)"
  else
    log_warning "  [webserver] OpenLiteSpeed not detected via systemd or lswsctrl"
  fi

  # 3. Port 80 open
  if _port_open 80; then
    log_success "  [webserver] port 80 responding"
  else
    log_error   "  [webserver] port 80 NOT responding"
    status=1
  fi

  # 4. HTTP request
  local http_code
  http_code="$(curl -fsSL --max-time 5 -o /dev/null -w "%{http_code}" "http://127.0.0.1/" 2>/dev/null || echo "000")"
  if [[ "$http_code" =~ ^[23] ]]; then
    log_success "  [webserver] HTTP GET / returned $http_code"
  else
    log_warning "  [webserver] HTTP GET / returned $http_code"
  fi

  # 5. Admin port
  if _port_open "${OLS_ADMIN_PORT:-8090}"; then
    log_success "  [webserver] OLS admin port ${OLS_ADMIN_PORT:-8090} open"
  else
    log_warning "  [webserver] OLS admin port ${OLS_ADMIN_PORT:-8090} not responding"
  fi

  return $status
}
