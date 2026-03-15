#!/usr/bin/env bash
# =============================================================================
#  HS-Panel — Production Installer Orchestrator
#  https://hostingsignal.in
#
#  Usage:
#    curl -sL https://install.hostingsignal.in | sudo bash
#    — OR —
#    sudo bash installer/install.sh [OPTIONS]
#
#  Options:
#    --skip-firewall     Skip firewall configuration
#    --skip-services     Skip service installation (panel only)
#    --skip-mail         Skip Postfix + Dovecot installation
#    --skip-dns          Skip PowerDNS installation
#    --dev               Development mode (relaxed checks)
#    --unattended        Non-interactive mode
#    --help              Show this help text
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ─── Paths ──────────────────────────────────────────────────────────────────
readonly INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
readonly LOG_FILE="/var/log/hspanel-install.log"
readonly CREDS_FILE="/root/hspanel_credentials.txt"
readonly ENV_DIR="/etc/hostingsignal"
readonly INSTALL_START="$(date '+%Y-%m-%d %H:%M:%S')"

# ─── Default flags ───────────────────────────────────────────────────────────
SKIP_FIREWALL=false
SKIP_SERVICES=false
SKIP_MAIL=false
SKIP_DNS=false
DEV_MODE=false
UNATTENDED=false

# ─── Source core modules ─────────────────────────────────────────────────────
_src() { source "${INSTALLER_DIR}/core/${1}"; }

_src logger.sh
_src os_detector.sh
_src dependency_manager.sh
_src firewall_config.sh
_src rollback_manager.sh
_src service_orchestrator.sh

# ─── Source health checks ─────────────────────────────────────────────────────
_hc() { source "${INSTALLER_DIR}/healthchecks/${1}"; }

# Helper shared by health-check scripts
_port_open() {
  local port="$1"
  (echo >/dev/tcp/127.0.0.1/"$port") &>/dev/null
}

_hc check_webserver.sh
_hc check_database.sh
_hc check_mail.sh
_hc check_dns.sh
_hc check_panel_api.sh

# ─── Parse arguments ─────────────────────────────────────────────────────────
_usage() {
  cat <<EOF
Usage: sudo bash install.sh [OPTIONS]

Options:
  --skip-firewall     Skip firewall configuration
  --skip-services     Skip service installation (panel only)
  --skip-mail         Skip Postfix + Dovecot
  --skip-dns          Skip PowerDNS
  --dev               Development / relaxed mode
  --unattended        Non-interactive (no prompts)
  --help              Show this help
EOF
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --skip-firewall) SKIP_FIREWALL=true ;;
    --skip-services) SKIP_SERVICES=true ;;
    --skip-mail)     SKIP_MAIL=true ;;
    --skip-dns)      SKIP_DNS=true ;;
    --dev)           DEV_MODE=true ;;
    --unattended)    UNATTENDED=true ;;
    --help|-h)       _usage ;;
    *)               log_warning "Unknown option: $arg" ;;
  esac
done

# ─── Ensure log file exists ───────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
exec 2> >(tee -a "$LOG_FILE" >&2)

# ─── Global trap ─────────────────────────────────────────────────────────────
trap '_on_err "$LINENO" "$BASH_COMMAND"' ERR

_on_err() {
  local line="$1"
  local cmd="$2"
  log_error "FATAL: command failed at line $line: $cmd"
  log_rollback "Starting rollback procedure…"
  run_rollback 2>&1 | tee -a "$LOG_FILE"
  log_error "Installation FAILED. See $LOG_FILE for details."
  exit 1
}

# ─── Step counter ────────────────────────────────────────────────────────────
STEP_NUM=0
STEP_TOTAL=9

_step() {
  (( STEP_NUM++ )) || true
  log_section "Step ${STEP_NUM}/${STEP_TOTAL} — ${1}"
}

# =============================================================================
#  PHASES
# =============================================================================

# Phase 0 — Banner
_phase_banner() {
  clear 2>/dev/null || true
  printf '%b' "${BOLD}${CYAN}"
  cat <<'BANNER'
  ██╗  ██╗███████╗    ██████╗  █████╗ ███╗   ██╗███████╗██╗
  ██║  ██║██╔════╝    ██╔══██╗██╔══██╗████╗  ██║██╔════╝██║
  ███████║███████╗    ██████╔╝███████║██╔██╗ ██║█████╗  ██║
  ██╔══██║╚════██║    ██╔═══╝ ██╔══██║██║╚██╗██║██╔══╝  ██║
  ██║  ██║███████║    ██║     ██║  ██║██║ ╚████║███████╗███████╗
  ╚═╝  ╚═╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
BANNER
  printf '%b' "${RESET}"
  printf '%b\n' "  ${DIM}Production Hosting Control Panel — installer v1.0.0${RESET}"
  printf '%b\n' "  ${DIM}https://hostingsignal.in${RESET}"
  echo
  printf '%b\n' "  ${YELLOW}Started at: ${INSTALL_START}${RESET}"
  echo
}

# Phase 1 — Preflight
_phase_preflight() {
  _step "Preflight checks"

  # Root check
  if [[ "$(id -u)" -ne 0 ]]; then
    log_error "This installer must be run as root."
    exit 1
  fi
  log_success "Running as root"

  # Disk space (>= 5 GB free on /)
  local free_kb
  free_kb="$(df -k / | awk 'NR==2{print $4}')"
  if [[ "$free_kb" -lt 5242880 ]]; then
    log_error "Insufficient disk space. Need >= 5 GB free on /, have $(( free_kb / 1024 / 1024 )) GB."
    exit 1
  fi
  log_success "Disk space OK ($(( free_kb / 1024 / 1024 )) GB free)"

  # RAM >= 1 GB
  local ram_mb
  ram_mb="$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)"
  if [[ "$ram_mb" -lt 1024 ]]; then
    if $DEV_MODE; then
      log_warning "RAM < 1 GB ($ram_mb MB) — continuing in dev mode"
    else
      log_error "Insufficient RAM. Need >= 1 GB, have ${ram_mb} MB."
      exit 1
    fi
  fi
  log_success "RAM OK (${ram_mb} MB)"

  # Internet connectivity
  if ! curl -s --connect-timeout 5 https://1.1.1.1 &>/dev/null; then
    log_error "No internet connectivity detected."
    exit 1
  fi
  log_success "Internet connectivity OK"

  # Detect OS
  detect_os
  assert_supported_os
  print_os_info

  # Confirm (interactive mode)
  if ! $UNATTENDED; then
    echo
    printf '%b' "  ${BOLD}Proceed with installation? [y/N] ${RESET}"
    local confirm
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      log_warning "Installation cancelled by user."
      exit 0
    fi
  fi
}

# Phase 2 — System update + common deps
_phase_dependencies() {
  _step "System update and common dependencies"
  update_system
  install_common_dependencies
  install_nodejs
}

# Phase 3 — Services (dependency-ordered)
_phase_services() {
  $SKIP_SERVICES && { log_warning "Skipping service installation (--skip-services)"; return 0; }

  _step "Service installation"

  print_dependency_graph

  # Source all service installers
  local svc_dir="${INSTALLER_DIR}/services"
  source "${svc_dir}/install_openlitespeed.sh"
  source "${svc_dir}/install_mariadb.sh"
  source "${svc_dir}/install_php.sh"
  source "${svc_dir}/install_phpmyadmin.sh"
  source "${svc_dir}/install_postfix.sh"
  source "${svc_dir}/install_dovecot.sh"
  source "${svc_dir}/install_rainloop.sh"
  source "${svc_dir}/install_powerdns.sh"

  # Determine installation order
  local services=("openlitespeed" "mariadb" "php" "phpmyadmin")
  if ! $SKIP_MAIL; then
    services+=("postfix" "dovecot" "rainloop")
  fi
  if ! $SKIP_DNS; then
    services+=("powerdns")
  fi

  local order
  mapfile -t order < <(resolve_order "${services[@]}")

  local total_svc="${#order[@]}"
  local done_svc=0

  for svc in "${order[@]}"; do
    (( done_svc++ )) || true
    progress_bar "$done_svc" "$total_svc" "Services"

    if ! deps_satisfied "$svc"; then
      log_error "Dependencies not satisfied for $svc — aborting"
      mark_service_failed "$svc"
      continue
    fi

    log_step "Installing: $svc"

    case "$svc" in
      openlitespeed) install_openlitespeed && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      mariadb)       install_mariadb      && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      php)           install_php          && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      phpmyadmin)    install_phpmyadmin   && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      postfix)       install_postfix      && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      dovecot)       install_dovecot      && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      rainloop)      install_rainloop     && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      powerdns)      install_powerdns     && mark_service_done "$svc" || mark_service_failed "$svc" ;;
      *)             log_warning "Unknown service: $svc"; mark_service_skipped "$svc" ;;
    esac
  done

  progress_bar "$total_svc" "$total_svc" "Services"
  echo
}

# Phase 4 — Panel
_phase_panel() {
  _step "HS-Panel installation"

  source "${INSTALLER_DIR}/panel/configure_env.sh"
  source "${INSTALLER_DIR}/panel/install_hspanel.sh"

  configure_env
  install_hspanel
}

# Phase 5 — Firewall
_phase_firewall() {
  $SKIP_FIREWALL && { log_warning "Skipping firewall configuration (--skip-firewall)"; return 0; }
  _step "Firewall configuration"
  configure_firewall
}

# Phase 6 — Health checks
_phase_healthchecks() {
  _step "Running health checks"

  local hc_pass=0
  local hc_fail=0
  local fail_list=()

  _run_hc() {
    local name="$1"
    local fn="$2"
    printf '%b' "  ${CYAN}[health]${RESET} ${name}…"
    if $fn; then
      (( hc_pass++ )) || true
      printf '%b\n' " ${GREEN}PASS${RESET}"
    else
      (( hc_fail++ )) || true
      fail_list+=("$name")
      printf '%b\n' " ${RED}FAIL${RESET}"
    fi
  }

  _run_hc "Web Server"  check_webserver
  _run_hc "Database"    check_database
  if ! $SKIP_MAIL; then
    _run_hc "Mail"      check_mail
  fi
  if ! $SKIP_DNS; then
    _run_hc "DNS"       check_dns
  fi
  _run_hc "Panel API"   check_panel_api

  echo
  log_kv "Health checks passed" "$hc_pass"
  log_kv "Health checks failed" "$hc_fail"

  if [[ "$hc_fail" -gt 0 ]]; then
    log_warning "Failed components: ${fail_list[*]}"
    log_warning "Panel installed but some services may be unhealthy. Check $LOG_FILE"
  fi
}

# Phase 7 — Summary
_phase_summary() {
  _step "Installation summary"

  local end_time
  end_time="$(date '+%Y-%m-%d %H:%M:%S')"

  # Read credentials if present
  local admin_pass=""
  local db_pass=""
  local api_key=""
  if [[ -f "$CREDS_FILE" ]]; then
    admin_pass="$(grep 'Panel Admin Password' "$CREDS_FILE" 2>/dev/null | awk -F': ' '{print $2}' | tr -d '[:space:]' || echo '<see /root/hspanel_credentials.txt>')"
    db_pass="$(grep 'MariaDB App Password' "$CREDS_FILE" 2>/dev/null | awk -F': ' '{print $2}' | tr -d '[:space:]' || echo '<see /root/hspanel_credentials.txt>')"
    api_key="$(grep 'Panel API Key' "$CREDS_FILE" 2>/dev/null | awk -F': ' '{print $2}' | tr -d '[:space:]' || echo '<see /root/hspanel_credentials.txt>')"
    local ols_pass
    ols_pass="$(grep 'OpenLiteSpeed Admin Password' "$CREDS_FILE" 2>/dev/null | awk -F': ' '{print $2}' | tr -d '[:space:]' || echo '<see /root/hspanel_credentials.txt>')"
  fi

  local server_ip
  server_ip="$(curl -s --connect-timeout 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"

  printf '%b\n' ""
  printf '%b\n' "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
  printf '%b\n' "${BOLD}${GREEN}║     HS-Panel Installation Complete!                         ║${RESET}"
  printf '%b\n' "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo
  printf '%b\n' "  ${BOLD}Access URLs${RESET}"
  printf '%b\n' "  ──────────────────────────────────────────────"
  printf '%b\n' "  Panel UI    : ${CYAN}http://${server_ip}:3000${RESET}"
  printf '%b\n' "  Panel API   : ${CYAN}http://${server_ip}:2087${RESET}"
  printf '%b\n' "  OLS Admin   : ${CYAN}https://${server_ip}:7080${RESET}"
  printf '%b\n' "  phpMyAdmin  : ${CYAN}http://${server_ip}/phpmyadmin${RESET}"
  printf '%b\n' "  Webmail     : ${CYAN}http://${server_ip}/webmail${RESET}"
  echo
  printf '%b\n' "  ${BOLD}Credentials${RESET}"
  printf '%b\n' "  ──────────────────────────────────────────────"
  printf '%b\n' "  Panel Admin Pass    : ${YELLOW}${admin_pass}${RESET}"
  printf '%b\n' "  MariaDB App Pass    : ${YELLOW}${db_pass}${RESET}"
  printf '%b\n' "  Panel API Key       : ${YELLOW}${api_key}${RESET}"
  if [[ -n "${ols_pass:-}" ]]; then
    printf '%b\n' "  OLS Admin Pass      : ${YELLOW}${ols_pass}${RESET}"
  fi
  echo
  printf '%b\n' "  ${BOLD}Important files${RESET}"
  printf '%b\n' "  ──────────────────────────────────────────────"
  printf '%b\n' "  Credentials : ${DIM}${CREDS_FILE}${RESET}"
  printf '%b\n' "  Env file    : ${DIM}${ENV_DIR}/hostingsignal-devapi.env${RESET}"
  printf '%b\n' "  Install log : ${DIM}${LOG_FILE}${RESET}"
  printf '%b\n' "  Panel dir   : ${DIM}/usr/local/hspanel${RESET}"
  echo
  printf '%b\n' "  ${BOLD}Timing${RESET}"
  printf '%b\n' "  ──────────────────────────────────────────────"
  printf '%b\n' "  Started  : ${DIM}${INSTALL_START}${RESET}"
  printf '%b\n' "  Finished : ${DIM}${end_time}${RESET}"
  echo
  printf '%b\n' "  ${DIM}Need help? https://docs.hostingsignal.in${RESET}"
  printf '%b\n' "  ${DIM}Support:   support@hostingsignal.in${RESET}"
  echo
}

# =============================================================================
#  MAIN
# =============================================================================
main() {
  # Redirect all output to log as well
  exec > >(tee -a "$LOG_FILE") 2>&1

  _phase_banner
  _phase_preflight
  _phase_dependencies
  _phase_services
  _phase_panel
  _phase_firewall
  _phase_healthchecks
  _phase_summary
}

main "$@"
