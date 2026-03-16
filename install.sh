#!/usr/bin/env bash
set -euo pipefail

PREFIX="[HostingSignal]"
REPO_OWNER="${HS_REPO_OWNER:-limbanidhairya}"
REPO_NAME="${HS_REPO_NAME:-hostingsignal}"
REPO_REF="${HS_REPO_REF:-main}"
INSTALL_DIR="${HS_INSTALL_DIR:-/opt/hostingsignal}"

OS_ID=""
OS_VERSION_ID=""
PKG_MANAGER=""

TARGET_USER="${SUDO_USER:-${USER:-root}}"

log() {
  echo "${PREFIX} $*"
}

warn() {
  echo "${PREFIX} WARNING: $*"
}

fail() {
  echo "${PREFIX} ERROR: $*" >&2
  exit 1
}

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    fail "Please run as root or with sudo."
  fi
}

detect_os() {
  [[ -f /etc/os-release ]] || fail "Cannot detect OS: /etc/os-release not found."

  # shellcheck disable=SC1091
  source /etc/os-release
  OS_ID="${ID:-}"
  OS_VERSION_ID="${VERSION_ID:-}"

  case "${OS_ID}:${OS_VERSION_ID}" in
    ubuntu:22.04|ubuntu:24.04|debian:12)
      PKG_MANAGER="apt"
      ;;
    almalinux:8|almalinux:9|centos:9)
      PKG_MANAGER="dnf"
      ;;
    *)
      fail "Unsupported OS: ${OS_ID} ${OS_VERSION_ID}. Supported: Ubuntu 22.04/24.04, Debian 12, AlmaLinux 8/9, CentOS Stream 9."
      ;;
  esac

  # CentOS Stream 9 reports ID=centos VERSION_ID=9.
  if [[ "${OS_ID}" == "centos" && "${PKG_MANAGER}" != "dnf" ]]; then
    PKG_MANAGER="dnf"
  fi

  log "Detected OS: ${OS_ID} ${OS_VERSION_ID}"
}

detect_wsl() {
  if grep -qi microsoft /proc/version 2>/dev/null; then
    warn "WSL environment detected. Docker Desktop must be running with WSL integration enabled."
  fi
}

system_update() {
  log "Step 2 Update system"
  if [[ "${PKG_MANAGER}" == "apt" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt update -y
    apt upgrade -y
  else
    dnf update -y
  fi
}

apt_install_if_missing() {
  local cmd="$1"
  shift
  local pkgs=("$@")

  if command -v "${cmd}" >/dev/null 2>&1; then
    log "${cmd} already installed"
    return 0
  fi

  log "Installing ${pkgs[*]}"
  apt install -y "${pkgs[@]}"
}

dnf_install_if_missing() {
  local cmd="$1"
  shift
  local pkgs=("$@")

  if command -v "${cmd}" >/dev/null 2>&1; then
    log "${cmd} already installed"
    return 0
  fi

  log "Installing ${pkgs[*]}"
  dnf install -y "${pkgs[@]}"
}

install_dependencies() {
  log "Step 3 Install dependencies"
  log "Checking prerequisites"

  if [[ "${PKG_MANAGER}" == "apt" ]]; then
    apt_install_if_missing git git
    apt_install_if_missing curl curl
    apt_install_if_missing wget wget
    apt_install_if_missing jq jq
    apt_install_if_missing unzip unzip
    apt_install_if_missing tar tar
    apt_install_if_missing make build-essential
    apt_install_if_missing update-ca-certificates ca-certificates
  else
    dnf_install_if_missing git git
    dnf_install_if_missing curl curl
    dnf_install_if_missing wget wget
    dnf_install_if_missing jq jq
    dnf_install_if_missing unzip unzip
    dnf_install_if_missing tar tar
    dnf_install_if_missing make gcc gcc-c++ make
    dnf_install_if_missing update-ca-trust ca-certificates
  fi
}

install_docker() {
  log "Step 4 Install Docker"

  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed"
  else
    log "Installing Docker"

    if command -v curl >/dev/null 2>&1; then
      curl -fsSL https://get.docker.com | sh
    elif command -v wget >/dev/null 2>&1; then
      wget -qO- https://get.docker.com | sh
    else
      fail "curl or wget is required to install Docker"
    fi
  fi

  if command -v systemctl >/dev/null 2>&1; then
    systemctl enable docker || true
    systemctl start docker || true
  else
    warn "systemctl not available, skipping docker service enable/start"
  fi

  if ! getent group docker >/dev/null 2>&1; then
    groupadd docker || true
  fi

  usermod -aG docker "${TARGET_USER}" || true
  log "Added ${TARGET_USER} to docker group"
}

install_docker_compose() {
  log "Step 5 Install Docker Compose"

  if docker compose version >/dev/null 2>&1; then
    log "Docker Compose already installed"
    return 0
  fi

  log "Installing Docker Compose"
  if [[ "${PKG_MANAGER}" == "apt" ]]; then
    apt install -y docker-compose-plugin
  else
    dnf install -y docker-compose-plugin || true
  fi

  if ! docker compose version >/dev/null 2>&1; then
    local plugin_dir="/usr/local/lib/docker/cli-plugins"
    mkdir -p "${plugin_dir}"
    local arch
    arch="$(uname -m)"
    case "${arch}" in
      x86_64) arch="x86_64" ;;
      aarch64|arm64) arch="aarch64" ;;
      *) arch="x86_64" ;;
    esac

    local os
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    local url
    url="https://github.com/docker/compose/releases/latest/download/docker-compose-${os}-${arch}"

    if command -v curl >/dev/null 2>&1; then
      curl -fsSL "${url}" -o "${plugin_dir}/docker-compose"
    else
      wget -qO "${plugin_dir}/docker-compose" "${url}"
    fi
    chmod +x "${plugin_dir}/docker-compose"
  fi

  docker compose version >/dev/null 2>&1 || fail "Docker Compose installation failed"
}

clone_repo() {
  log "Step 6 Clone HS-Panel repo"
  local repo_url="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"

  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    log "Repo already exists at ${INSTALL_DIR}, pulling latest ${REPO_REF}"
    git -C "${INSTALL_DIR}" fetch --all --tags
    git -C "${INSTALL_DIR}" checkout "${REPO_REF}"
    git -C "${INSTALL_DIR}" pull --ff-only origin "${REPO_REF}"
  else
    rm -rf "${INSTALL_DIR}"
    git clone --depth 1 --branch "${REPO_REF}" "${repo_url}" "${INSTALL_DIR}"
  fi
}

start_services() {
  log "Step 7 Start services using docker compose"
  log "Starting containers"

  local compose_dir="${INSTALL_DIR}/deployment"
  local compose_file="${compose_dir}/docker-compose.yml"
  [[ -f "${compose_file}" ]] || fail "docker-compose.yml not found at ${compose_file}"

  cd "${compose_dir}"
  docker compose pull || true
  docker compose up -d --build
}

health_checks() {
  log "Step 8 Run health checks"

  local compose_dir="${INSTALL_DIR}/deployment"
  cd "${compose_dir}"

  docker compose ps

  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 10 "http://127.0.0.1:3000" >/dev/null && log "Frontend health check passed (3000)" || warn "Frontend not ready yet (3000)"
    curl -fsS --max-time 10 "http://127.0.0.1:2087/api/health" >/dev/null && log "API health check passed (2087)" || warn "API not ready yet (2087)"
  fi

  local unhealthy
  unhealthy="$(docker compose ps --format json 2>/dev/null | jq -r 'select(.Health != "" and .Health != "healthy") | .Service' || true)"
  if [[ -n "${unhealthy}" ]]; then
    warn "Some services are not healthy yet: ${unhealthy}"
  fi
}

main() {
  require_root

  log "Step 1 Detect OS"
  detect_os
  detect_wsl

  system_update
  install_dependencies
  install_docker
  install_docker_compose
  clone_repo
  start_services
  health_checks

  log "Installation completed"
  log "Run this once to refresh group in current shell: newgrp docker"
  log "Install location: ${INSTALL_DIR}"
}

main "$@"
