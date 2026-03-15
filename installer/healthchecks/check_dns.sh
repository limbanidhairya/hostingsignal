#!/usr/bin/env bash
# HS-Panel Health Check — DNS (PowerDNS)

check_dns() {
  local status=0

  # 1. Service
  if systemctl is-active --quiet pdns 2>/dev/null; then
    log_success "  [dns] PowerDNS service active"
  else
    log_error   "  [dns] PowerDNS service NOT active"
    status=1
    return $status
  fi

  # 2. TCP port 53
  if _port_open 53; then
    log_success "  [dns] port 53/tcp open"
  else
    log_error   "  [dns] port 53/tcp NOT open"
    status=1
  fi

  # 3. UDP port 53 — use dig if available
  if command -v dig &>/dev/null; then
    local dig_out
    dig_out="$(dig @127.0.0.1 localhost A +time=2 +tries=1 2>&1 || true)"
    if echo "$dig_out" | grep -q "status: NOERROR\|status: NXDOMAIN"; then
      log_success "  [dns] DNS UDP query responded"
    else
      log_error   "  [dns] DNS UDP query failed"
      status=1
    fi
  elif command -v nslookup &>/dev/null; then
    if nslookup localhost 127.0.0.1 &>/dev/null; then
      log_success "  [dns] DNS query (nslookup) responded"
    else
      log_error   "  [dns] DNS query (nslookup) failed"
      status=1
    fi
  else
    log_warning "  [dns] dig/nslookup not found; skipping DNS query test"
  fi

  # 4. pdns_control ping
  if command -v pdns_control &>/dev/null; then
    if pdns_control ping 2>/dev/null | grep -q "PONG"; then
      log_success "  [dns] pdns_control ping OK"
    else
      log_error   "  [dns] pdns_control ping failed"
      status=1
    fi
  fi

  # 5. API
  local api_key
  api_key="$(grep -E '^api-key=' /etc/powerdns/pdns.conf 2>/dev/null | cut -d= -f2 | tr -d ' ' || true)"
  if [[ -n "$api_key" ]]; then
    local http_code
    http_code="$(curl -s -o /dev/null -w '%{http_code}' \
      -H "X-API-Key: $api_key" http://127.0.0.1:8053/api/v1/servers/localhost 2>/dev/null || echo 000)"
    if [[ "$http_code" == "200" ]]; then
      log_success "  [dns] PowerDNS API responding (HTTP 200)"
    else
      log_warning "  [dns] PowerDNS API returned HTTP $http_code"
    fi
  else
    log_warning "  [dns] Could not read PowerDNS API key; skipping API check"
  fi

  return $status
}
