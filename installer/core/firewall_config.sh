#!/usr/bin/env bash
# HS-Panel Installer — Firewall Configuration
# Configures UFW (Debian/Ubuntu) or Firewalld (RHEL/Alma/CentOS).

# ── Port definitions ──────────────────────────────────────────────────────────
declare -A HSPANEL_PORTS=(
  ["ssh"]="22/tcp"
  ["http"]="80/tcp"
  ["https"]="443/tcp"
  ["panel_http"]="2086/tcp"
  ["panel_https"]="2087/tcp"
  ["panel_api"]="3000/tcp"
  ["ols_admin"]="8090/tcp"
  ["smtp"]="25/tcp"
  ["smtps"]="465/tcp"
  ["submission"]="587/tcp"
  ["pop3"]="110/tcp"
  ["pop3s"]="995/tcp"
  ["imap"]="143/tcp"
  ["imaps"]="993/tcp"
  ["dns_tcp"]="53/tcp"
  ["dns_udp"]="53/udp"
  ["phpmyadmin"]="80/tcp"  # served under /phpmyadmin alias
)

# ── UFW helpers ───────────────────────────────────────────────────────────────
_ufw_open() {
  local port="$1"
  ufw allow "$port" > /dev/null 2>&1 || true
}

configure_firewall_ufw() {
  log_info "Configuring UFW firewall..."

  if ! command -v ufw &>/dev/null; then
    apt-get install -y -qq ufw
  fi

  # Reset to default deny
  ufw --force reset > /dev/null 2>&1

  # Open required ports
  for name in "${!HSPANEL_PORTS[@]}"; do
    _ufw_open "${HSPANEL_PORTS[$name]}"
    log_info "  UFW opened: ${HSPANEL_PORTS[$name]}  ($name)"
  done

  ufw default deny incoming  > /dev/null 2>&1
  ufw default allow outgoing > /dev/null 2>&1
  ufw --force enable         > /dev/null 2>&1

  log_success "UFW configured and enabled"
  ufw status numbered 2>/dev/null >> "$HSPANEL_LOG_FILE" || true
}

# ── Firewalld helpers ─────────────────────────────────────────────────────────
_firewalld_open() {
  local portproto="$1"
  firewall-cmd --permanent --add-port="$portproto" > /dev/null 2>&1 || true
}

configure_firewall_firewalld() {
  log_info "Configuring firewalld..."

  if ! systemctl is-active --quiet firewalld; then
    systemctl enable --now firewalld
  fi

  for name in "${!HSPANEL_PORTS[@]}"; do
    _firewalld_open "${HSPANEL_PORTS[$name]}"
    log_info "  Firewalld opened: ${HSPANEL_PORTS[$name]}  ($name)"
  done

  firewall-cmd --reload > /dev/null 2>&1
  log_success "Firewalld configured"
  firewall-cmd --list-all 2>/dev/null >> "$HSPANEL_LOG_FILE" || true
}

# ── Main entry point ──────────────────────────────────────────────────────────
configure_firewall() {
  if [[ "$OS_FAMILY" == "debian" ]]; then
    configure_firewall_ufw
  else
    configure_firewall_firewalld
  fi
}

# Convenience: print opened port table for summary
print_firewall_summary() {
  echo ""
  log_info "Opened firewall ports:"
  for name in "${!HSPANEL_PORTS[@]}"; do
    log_kv "  $name" "${HSPANEL_PORTS[$name]}"
  done
}
