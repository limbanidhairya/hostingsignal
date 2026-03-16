#!/usr/bin/env bash
# =============================================================================
# HostingSignal HS-Panel Native Installer
# Core services run directly on the host OS (no Docker for core stack).
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

readonly INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
readonly LOG_FILE="/var/log/hspanel_install.log"
readonly CREDS_FILE="/root/hspanel_credentials.txt"
readonly INSTALL_START="$(date '+%Y-%m-%d %H:%M:%S')"

SKIP_FIREWALL=false
SKIP_MAIL=false
SKIP_DNS=false
UNATTENDED=false

# Global install targets
export HSPANEL_INSTALL_DIR="${HSPANEL_INSTALL_DIR:-/opt/hostingsignal}"
export HSPANEL_ENV_FILE="${HSPANEL_ENV_FILE:-/opt/hostingsignal/deployment/hostingsignal-devapi.production.env}"
export HSPANEL_CREDS_FILE="${HSPANEL_CREDS_FILE:-$CREDS_FILE}"

_src() { source "${INSTALLER_DIR}/core/${1}"; }
_src logger.sh
_src os_detector.sh
_src dependency_manager.sh
_src firewall_config.sh
_src rollback_manager.sh

_hc() { source "${INSTALLER_DIR}/healthchecks/${1}"; }
_hc check_webserver.sh
_hc check_database.sh
_hc check_mail.sh
_hc check_dns.sh
_hc check_panel_api.sh

_port_open() {
  local port="$1"
  (echo >/dev/tcp/127.0.0.1/"$port") &>/dev/null
}

_usage() {
  cat <<EOF
Usage: sudo bash installer/install.sh [OPTIONS]

Options:
  --skip-firewall   Skip firewall configuration
  --skip-mail       Skip Postfix + Dovecot + Rainloop
  --skip-dns        Skip PowerDNS
  --unattended      Non-interactive mode
  --help            Show this help
EOF
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --skip-firewall) SKIP_FIREWALL=true ;;
    --skip-mail)     SKIP_MAIL=true ;;
    --skip-dns)      SKIP_DNS=true ;;
    --unattended)    UNATTENDED=true ;;
    --help|-h)       _usage ;;
    *)               log_warning "Unknown option: $arg" ;;
  esac
done

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1
exec 2> >(tee -a "$LOG_FILE" >&2)

trap '_on_err "$LINENO" "$BASH_COMMAND"' ERR
_on_err() {
  local line="$1"
  local cmd="$2"
  log_error "FATAL at line $line: $cmd"
  run_rollback 2>/dev/null || true
  log_error "Installer failed. Log: $LOG_FILE"
  exit 1
}

STEP_NUM=0
STEP_TOTAL=14
_step() {
  (( STEP_NUM++ )) || true
  log_section "Step ${STEP_NUM}/${STEP_TOTAL} — ${1}"
}

_preflight() {
  if [[ "$(id -u)" -ne 0 ]]; then
    log_error "Run installer as root."
    exit 1
  fi

  # Hard requirements for bootstrap and package operations.
  command -v bash >/dev/null 2>&1 || { log_error "bash is required"; exit 1; }
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    log_error "curl or wget is required for repository/bootstrap reachability checks"
    exit 1
  fi

  if is_wsl; then
    log_warning "WSL environment detected. Docker Desktop must be running with WSL integration enabled."
  fi

  # Strict repository reachability checks.
  local repo_ok=0
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 8 "https://github.com/limbanidhairya/hostingsignal" >/dev/null 2>&1 && repo_ok=1 || true
    curl -fsSL --max-time 8 "https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/installer/install.sh" >/dev/null 2>&1 && repo_ok=1 || true
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- --timeout=8 "https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/installer/install.sh" >/dev/null 2>&1 && repo_ok=1 || true
  fi

  if [[ "$repo_ok" -ne 1 ]]; then
    log_error "Unable to reach HostingSignal GitHub repository/raw installer URLs"
    exit 1
  fi

  if ! $UNATTENDED; then
    printf '%b' "${BOLD}Proceed with native HS-Panel installation? [y/N] ${RESET}"
    local confirm
    read -r confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { log_warning "Installation cancelled"; exit 0; }
  fi
}

_configure_selinux_for_alma() {
  if [[ "${OS_ID:-}" != "almalinux" ]]; then
    return 0
  fi
  if ! command -v getenforce >/dev/null 2>&1; then
    return 0
  fi

  local mode
  mode="$(getenforce 2>/dev/null || echo Disabled)"
  log_info "SELinux mode: ${mode}"

  if [[ "$mode" == "Enforcing" || "$mode" == "Permissive" ]]; then
    if ! command -v semanage >/dev/null 2>&1; then
      dnf install -y policycoreutils-python-utils >/dev/null 2>&1 || true
    fi

    # Allow web stack network/database relay paths commonly needed by HS-Panel.
    setsebool -P httpd_can_network_connect 1 >/dev/null 2>&1 || true
    setsebool -P httpd_can_network_connect_db 1 >/dev/null 2>&1 || true

    if command -v semanage >/dev/null 2>&1; then
      semanage port -a -t http_port_t -p tcp 2086 2>/dev/null || semanage port -m -t http_port_t -p tcp 2086 2>/dev/null || true
      semanage port -a -t http_port_t -p tcp 2087 2>/dev/null || semanage port -m -t http_port_t -p tcp 2087 2>/dev/null || true
      semanage port -a -t http_port_t -p tcp 3000 2>/dev/null || semanage port -m -t http_port_t -p tcp 3000 2>/dev/null || true
      semanage port -a -t http_port_t -p tcp 8090 2>/dev/null || semanage port -m -t http_port_t -p tcp 8090 2>/dev/null || true
    fi

    log_success "SELinux policy adjustments applied for AlmaLinux"
  fi
}

_install_services_native() {
  local svc_dir="${INSTALLER_DIR}/services"
  source "${svc_dir}/install_openlitespeed.sh"
  source "${svc_dir}/install_mariadb.sh"
  source "${svc_dir}/install_php.sh"
  source "${svc_dir}/install_phpmyadmin.sh"
  source "${svc_dir}/install_powerdns.sh"
  source "${svc_dir}/install_postfix.sh"
  source "${svc_dir}/install_dovecot.sh"
  source "${svc_dir}/install_rainloop.sh"

  _step "Detect OS"
  detect_os
  assert_supported_os
  print_os_info
  _configure_selinux_for_alma

  _step "Update system"
  update_system

  _step "Install dependencies"
  install_common_dependencies
  install_nodejs 20

  _step "Install OpenLiteSpeed"
  install_openlitespeed

  _step "Install MariaDB"
  install_mariadb

  _step "Install PHP versions"
  install_php
  install_phpmyadmin

  if ! $SKIP_DNS; then
    _step "Install PowerDNS"
    install_powerdns
  else
    _step "Install PowerDNS"
    log_warning "Skipping PowerDNS (--skip-dns)"
  fi

  if ! $SKIP_MAIL; then
    _step "Install Postfix + Dovecot"
    install_postfix
    install_dovecot

    _step "Install Rainloop"
    install_rainloop
  else
    _step "Install Postfix + Dovecot"
    log_warning "Skipping mail services (--skip-mail)"
    _step "Install Rainloop"
    log_warning "Skipping Rainloop (--skip-mail)"
  fi
}

_install_panel_native() {
  source "${INSTALLER_DIR}/panel/install_hspanel.sh"
  source "${INSTALLER_DIR}/panel/configure_env.sh"

  _step "Clone HS-Panel repository"
  install_hspanel

  _step "Generate env file"
  configure_env

  _step "Configure system services"
  configure_hspanel_systemd

  if ! $SKIP_FIREWALL; then
    configure_firewall
  else
    log_warning "Skipping firewall configuration (--skip-firewall)"
  fi

  _step "Start services"
  start_hspanel_services
}

_run_health_checks() {
  _step "Run health checks"

  local failed=0
  check_webserver || failed=1
  check_database || failed=1
  if ! $SKIP_MAIL; then
    check_mail || failed=1
  fi
  if ! $SKIP_DNS; then
    check_dns || failed=1
  fi
  check_panel_api || failed=1

  if [[ "$failed" -ne 0 ]]; then
    log_warning "One or more health checks failed. Review: $LOG_FILE"
  fi
}

_print_summary() {
  local ip
  ip="$(curl -fsSL --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"

  echo
  printf '%b\n' "${BOLD}${GREEN}HS-Panel Installed Successfully${RESET}"
  log_kv "Panel URL" "http://${ip}:2086"
  log_kv "Panel HTTPS" "https://${ip}:2087"
  log_kv "API" "http://${ip}:3000"
  log_kv "OpenLiteSpeed Admin" "http://${ip}:8090"
  log_kv "phpMyAdmin" "http://${ip}/phpmyadmin"
  log_kv "Webmail" "http://${ip}/webmail"
  log_kv "Install log" "$LOG_FILE"
  log_kv "Credentials" "$HSPANEL_CREDS_FILE"
  log_kv "Started" "$INSTALL_START"
  log_kv "Finished" "$(date '+%Y-%m-%d %H:%M:%S')"
}

main() {
  _preflight
  _install_services_native
  _install_panel_native
  _run_health_checks
  _print_summary
}

main "$@"
