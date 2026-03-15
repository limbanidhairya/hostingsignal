#!/usr/bin/env bash
# HS-Panel Health Check — Panel API + Web UI

check_panel_api() {
  local status=0

  # --- Backend API (port 2087) ---
  for svc in hostingsignal-api hspanel-api; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      log_success "  [panel] $svc service active"
      break
    fi
  done

  if _port_open 2087; then
    log_success "  [panel] API port 2087 open"
  else
    log_error   "  [panel] API port 2087 NOT open"
    status=1
  fi

  # Health endpoint
  local http_code
  http_code="$(curl -s -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:2087/api/health 2>/dev/null || echo 000)"
  if [[ "$http_code" == "200" ]]; then
    log_success "  [panel] /api/health returned HTTP 200"
  elif [[ "$http_code" == "000" ]]; then
    log_error   "  [panel] /api/health unreachable"
    status=1
  else
    log_warning "  [panel] /api/health returned HTTP $http_code"
  fi

  # --- Web UI (port 3000) ---
  for svc in hostingsignal-web hspanel-web; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      log_success "  [panel] $svc service active"
      break
    fi
  done

  if _port_open 3000; then
    log_success "  [panel] Web UI port 3000 open"
  else
    log_error   "  [panel] Web UI port 3000 NOT open"
    status=1
  fi

  http_code="$(curl -s -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:3000 2>/dev/null || echo 000)"
  if [[ "$http_code" =~ ^(200|301|302)$ ]]; then
    log_success "  [panel] Web UI HTTP $http_code"
  else
    log_error   "  [panel] Web UI returned HTTP $http_code"
    status=1
  fi

  # --- Virtual IP admin panel (port 2086) ---
  if _port_open 2086; then
    log_success "  [panel] Admin UI port 2086 open"
  else
    log_warning "  [panel] Admin UI port 2086 NOT open (may not be started yet)"
  fi

  # --- Panel files ---
  local panel_dir="/usr/local/hspanel"
  if [[ -d "$panel_dir" ]]; then
    log_success "  [panel] panel directory exists ($panel_dir)"
  else
    log_error   "  [panel] panel directory NOT found ($panel_dir)"
    status=1
  fi

  local env_file="/etc/hostingsignal/hostingsignal-devapi.env"
  if [[ -f "$env_file" ]]; then
    log_success "  [panel] environment file present"
  else
    log_error   "  [panel] environment file missing ($env_file)"
    status=1
  fi

  return $status
}
