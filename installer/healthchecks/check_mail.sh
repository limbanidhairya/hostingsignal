#!/usr/bin/env bash
# HS-Panel Health Check — Mail (Postfix + Dovecot)

check_mail() {
  local status=0

  # --- Postfix ---
  if systemctl is-active --quiet postfix 2>/dev/null; then
    log_success "  [mail] Postfix service active"
  else
    log_error   "  [mail] Postfix service NOT active"
    status=1
  fi

  for port in 25 465 587; do
    if _port_open $port; then
      log_success "  [mail] SMTP port $port open"
    else
      log_error   "  [mail] SMTP port $port NOT open"
      status=1
    fi
  done

  # SMTP banner
  local banner
  banner="$(echo QUIT | nc -w3 127.0.0.1 25 2>/dev/null | head -1 || true)"
  if [[ "$banner" == "220"* ]]; then
    log_success "  [mail] SMTP 220 banner received"
  else
    log_error   "  [mail] SMTP banner check FAILED (got: ${banner:-<none>})"
    status=1
  fi

  # --- Dovecot ---
  if systemctl is-active --quiet dovecot 2>/dev/null; then
    log_success "  [mail] Dovecot service active"
  else
    log_error   "  [mail] Dovecot service NOT active"
    status=1
  fi

  for port in 143 993 110 995; do
    if _port_open $port; then
      log_success "  [mail] port $port open"
    else
      log_warning "  [mail] port $port NOT open"
    fi
  done

  # Dovecot auth socket
  local auth_sock="/var/spool/postfix/private/auth"
  if [[ -S "$auth_sock" ]]; then
    log_success "  [mail] Dovecot SASL socket present"
  else
    log_error   "  [mail] Dovecot SASL socket missing ($auth_sock)"
    status=1
  fi

  return $status
}
