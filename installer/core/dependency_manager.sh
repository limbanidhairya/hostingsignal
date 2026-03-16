#!/usr/bin/env bash
# HS-Panel Installer — Dependency Manager
# Installs OS packages required before any service installer runs.

# ── Common packages needed on all supported OS ──────────────────────────────
_COMMON_PKGS_DEBIAN=(
  curl wget git unzip zip tar gnupg2 lsb-release
  software-properties-common ca-certificates apt-transport-https
  ncurses-bin
  python3 python3-pip python3-venv
  build-essential make gcc
  netcat-openbsd quota
  sqlite3
  net-tools dnsutils bind9-utils
  cron logrotate sudo
)

_COMMON_PKGS_RHEL=(
  curl wget git unzip zip tar gnupg2
  ca-certificates
  python3 python3-pip
  gcc make
  nc quota
  sqlite
  net-tools bind-utils
  cronie logrotate sudo
  epel-release
)

# ── Install all common dependencies ─────────────────────────────────────────
install_common_dependencies() {
  log_info "Installing system dependencies..."

  if [[ "$OS_FAMILY" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq "${_COMMON_PKGS_DEBIAN[@]}"

  elif [[ "$OS_FAMILY" == "rhel" ]]; then
    dnf install -y epel-release 2>/dev/null || true
    dnf install -y "${_COMMON_PKGS_RHEL[@]}" --skip-broken
  fi

  log_success "Common dependencies installed"
}

# ── Package check/install helpers ────────────────────────────────────────────
pkg_installed() {
  local pkg="$1"
  if [[ "$OS_FAMILY" == "debian" ]]; then
    dpkg -l "$pkg" 2>/dev/null | grep -q '^ii'
  else
    rpm -q "$pkg" &>/dev/null
  fi
}

pkg_install() {
  local pkg="$1"
  if pkg_installed "$pkg"; then
    log_info "Package '$pkg' already installed — skipping"
    return 0
  fi
  if [[ "$OS_FAMILY" == "debian" ]]; then
    apt-get install -y -qq "$pkg"
  else
    dnf install -y "$pkg" --skip-broken
  fi
}

# ── System update ────────────────────────────────────────────────────────────
update_system() {
  log_info "Updating system packages..."
  if [[ "$OS_FAMILY" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive

    # Pre-flight: if apt-get upgrade pulls in a MariaDB/MySQL update, the
    # dpkg post-install script will try to (re)start the daemon.  If port 3306
    # is already in use that start fails and dpkg aborts with error code 1.
    # Stop any running MySQL/MariaDB now so the post-install hook can safely
    # restart after the upgrade.
    for _svc in mariadb mysql mysqld; do
      if systemctl is-active --quiet "$_svc" 2>/dev/null; then
        log_warning "[update_system] Stopping ${_svc} before upgrade to avoid port-3306 conflict"
        systemctl stop "$_svc" 2>/dev/null || true
      fi
    done

    apt-get update -qq
    apt-get upgrade -y -qq \
      -o 'Dpkg::Options::=--force-confdef' \
      -o 'Dpkg::Options::=--force-confold'

    # Restart MariaDB/MySQL if it was installed (the installer step will
    # manage the full setup, but the DB should be up for any remaining
    # upgrade post-install hooks that query it)
    for _svc in mariadb mysql; do
      if systemctl list-unit-files --type=service 2>/dev/null | grep -q "^${_svc}\.service"; then
        systemctl start "$_svc" 2>/dev/null || true
        break
      fi
    done
  else
    dnf update -y --skip-broken
  fi
  log_success "System updated"
}

# ── Node.js (required for panel web frontend) ────────────────────────────────
install_nodejs() {
  local version="${1:-20}"
  if command -v node &>/dev/null; then
    local installed
    installed="$(node --version | cut -d. -f1 | tr -d 'v')"
    if [[ "$installed" -ge "$version" ]]; then
      log_info "Node.js $(node --version) already installed — skipping"
      return 0
    fi
  fi

  log_info "Installing Node.js $version..."
  if [[ "$OS_FAMILY" == "debian" ]]; then
    curl -fsSL "https://deb.nodesource.com/setup_${version}.x" | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs
  else
    curl -fsSL "https://rpm.nodesource.com/setup_${version}.x" | bash - > /dev/null 2>&1
    dnf install -y nodejs
  fi
  log_success "Node.js $(node --version) installed"
}

# ── Docker (optional for container runner) ───────────────────────────────────
install_docker() {
  if command -v docker &>/dev/null; then
    log_info "Docker $(docker --version | awk '{print $3}' | tr -d ',') already installed"
    return 0
  fi

  log_info "Installing Docker..."
  curl -fsSL https://get.docker.com | sh > /dev/null 2>&1
  usermod -aG docker "${SUDO_USER:-root}" 2>/dev/null || true
  systemctl enable --now docker
  log_success "Docker installed"
}
