#!/usr/bin/env bash
# HS-Panel Installer — OS Detector
# Sets: OS_ID, OS_VERSION_ID, OS_PRETTY_NAME, OS_CODENAME,
#       PKG_MANAGER, SVC_MANAGER, OS_FAMILY (debian|rhel)

detect_os() {
  if [[ ! -f /etc/os-release ]]; then
    log_error "Cannot detect OS: /etc/os-release not found"
    exit 1
  fi

  # shellcheck source=/dev/null
  source /etc/os-release

  OS_ID="${ID:-unknown}"
  OS_VERSION_ID="${VERSION_ID:-unknown}"
  OS_PRETTY_NAME="${PRETTY_NAME:-$OS_ID $OS_VERSION_ID}"
  OS_CODENAME="${VERSION_CODENAME:-}"

  case "$OS_ID" in
    ubuntu|debian|raspbian)
      OS_FAMILY="debian"
      PKG_MANAGER="apt"
      SVC_MANAGER="systemctl"
      ;;
    almalinux|rocky|centos|rhel|ol)
      OS_FAMILY="rhel"
      PKG_MANAGER="dnf"
      SVC_MANAGER="systemctl"
      ;;
    *)
      log_error "Unsupported OS: $OS_PRETTY_NAME"
      log_error "Supported: Ubuntu 22.04/24.04, Debian 12, AlmaLinux 8/9, CentOS Stream 9"
      exit 1
      ;;
  esac

  export OS_ID OS_VERSION_ID OS_PRETTY_NAME OS_CODENAME OS_FAMILY PKG_MANAGER SVC_MANAGER
}

assert_supported_os() {
  detect_os

  local supported=0
  case "$OS_ID:$OS_VERSION_ID" in
    ubuntu:22.04|ubuntu:24.04)      supported=1 ;;
    debian:12)                       supported=1 ;;
    almalinux:8|almalinux:9)        supported=1 ;;
    rocky:8|rocky:9)                 supported=1 ;;
    centos:9|centos:*)               supported=1 ;;
  esac

  if [[ "$supported" -eq 0 ]]; then
    log_warning "OS '$OS_PRETTY_NAME' is not in the verified support matrix."
    log_warning "Installation may succeed but is not officially tested."
  fi

  log_success "Detected OS: $OS_PRETTY_NAME (family: $OS_FAMILY)"
}

# Returns 0 if running inside WSL
is_wsl() {
  if [[ -f /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null; then
    return 0
  fi
  [[ -n "${WSL_INTEROP:-}" ]] && return 0
  return 1
}

# Print OS information table
print_os_info() {
  log_kv "OS"        "$OS_PRETTY_NAME"
  log_kv "Family"    "$OS_FAMILY"
  log_kv "Package"   "$PKG_MANAGER"
  log_kv "Services"  "$SVC_MANAGER"
  if is_wsl; then
    log_kv "Runtime" "WSL2"
  fi
}
