#!/usr/bin/env bash
# HS-Panel Health Check — Panel API + Web UI

check_panel_api() {
  local status=0

  _restart_panel_stack() {
    systemctl restart hspanel-api 2>/dev/null || systemctl restart hostingsignal-api 2>/dev/null || true
    systemctl restart hspanel-web 2>/dev/null || systemctl restart hostingsignal-web 2>/dev/null || true
    systemctl restart lsws 2>/dev/null || systemctl restart lshttpd 2>/dev/null || true
    sleep 3
  }

  # --- Backend API (port 3000) ---
  for svc in hspanel-api hostingsignal-api; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      log_success "  [panel] $svc service active"
      break
    fi
  done

  if _port_open 3000; then
    log_success "  [panel] API port 3000 open"
  else
    log_warning "  [panel] API port 3000 NOT open - restarting panel stack"
    _restart_panel_stack
    if _port_open 3000; then
      log_success "  [panel] API port 3000 open after restart"
    else
      log_error   "  [panel] API port 3000 NOT open"
      status=1
    fi
  fi

  # Health endpoint
  local http_code
  http_code="$(curl -s -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:3000/health 2>/dev/null || echo 000)"
  if [[ "$http_code" == "200" ]]; then
    log_success "  [panel] /health returned HTTP 200"
  elif [[ "$http_code" == "000" ]]; then
    log_warning "  [panel] /health unreachable - restarting panel stack"
    _restart_panel_stack
    http_code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/health 2>/dev/null || echo 000)"
    if [[ "$http_code" == "200" ]]; then
      log_success "  [panel] /health returned HTTP 200 after restart"
    else
      log_error   "  [panel] /health unreachable"
      status=1
    fi
  else
    log_warning "  [panel] /health returned HTTP $http_code"
  fi

  # --- Native panel daemon ports ---
  for svc in hspanel-daemon hostingsignal-daemon; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      log_success "  [panel] $svc service active"
      break
    fi
  done

  if _port_open 2086; then
    log_success "  [panel] Panel HTTP port 2086 open"
  else
    log_warning "  [panel] Panel HTTP port 2086 NOT open - restarting panel stack"
    _restart_panel_stack
    _port_open 2086 && log_success "  [panel] Panel HTTP port 2086 open after restart" || log_warning "  [panel] Panel HTTP port 2086 NOT open"
  fi

  if _port_open 2087; then
    log_success "  [panel] Panel HTTPS port 2087 open"
  else
    log_warning "  [panel] Panel HTTPS port 2087 NOT open - restarting panel stack"
    _restart_panel_stack
    _port_open 2087 && log_success "  [panel] Panel HTTPS port 2087 open after restart" || log_warning "  [panel] Panel HTTPS port 2087 NOT open"
  fi

  if _port_open 8090; then
    log_success "  [panel] OLS Admin port 8090 open"
  else
    log_warning "  [panel] OLS Admin port 8090 NOT open - restarting OpenLiteSpeed"
    systemctl restart lsws 2>/dev/null || systemctl restart lshttpd 2>/dev/null || true
    sleep 3
    _port_open 8090 && log_success "  [panel] OLS Admin port 8090 open after restart" || log_warning "  [panel] OLS Admin port 8090 NOT open"
  fi

  local panel_http
  panel_http="$(curl -s -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:2086 2>/dev/null || echo 000)"
  if [[ "$panel_http" =~ ^(200|301|302|401|403)$ ]]; then
    log_success "  [panel] panel endpoint HTTP $panel_http"
  else
    log_warning "  [panel] panel endpoint returned HTTP $panel_http - restarting panel stack"
    _restart_panel_stack
    panel_http="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2086 2>/dev/null || echo 000)"
    [[ "$panel_http" =~ ^(200|301|302|401|403)$ ]] && log_success "  [panel] panel endpoint HTTP $panel_http after restart" || log_warning "  [panel] panel endpoint returned HTTP $panel_http"
  fi

  # --- Worker service ---
  if systemctl is-active --quiet hspanel-worker 2>/dev/null || systemctl is-active --quiet hostingsignal-taskd 2>/dev/null; then
    log_success "  [panel] worker service active"
  else
    log_error   "  [panel] worker service NOT active"
    status=1
  fi

  # --- Panel files ---
  local panel_dir="/opt/hostingsignal"
  if [[ -d "$panel_dir" ]]; then
    log_success "  [panel] panel directory exists ($panel_dir)"
  else
    log_error   "  [panel] panel directory NOT found ($panel_dir)"
    status=1
  fi

  local env_file="/opt/hostingsignal/deployment/hostingsignal-devapi.production.env"
  if [[ -f "$env_file" ]]; then
    log_success "  [panel] environment file present"
  else
    log_error   "  [panel] environment file missing ($env_file)"
    status=1
  fi

  return $status
}
