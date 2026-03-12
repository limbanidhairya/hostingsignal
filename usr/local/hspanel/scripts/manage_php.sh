#!/usr/bin/env bash
###############################################################################
# HostingSignal — PHP Multi-Version Manager
# Manages OpenLiteSpeed LSPHP packages across multiple PHP versions.
#
# Usage:
#   ./manage_php.sh install   <7.4|8.0|8.1|8.2|8.3|8.4>
#   ./manage_php.sh uninstall <version>
#   ./manage_php.sh list
#   ./manage_php.sh set-default <version>
#   ./manage_php.sh status
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLS_LSPHP_BASE="/usr/local/lsws"
LOG="${SCRIPT_DIR}/../../logs/php-manager.log"
mkdir -p "$(dirname "${LOG}")"

OS=""
VERSION=""

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[PHP]${NC} $*" | tee -a "${LOG}"; }
fail() { echo -e "${RED}[PHP][ERROR]${NC} $*" | tee -a "${LOG}"; exit 1; }
warn() { echo -e "${YELLOW}[PHP][WARN]${NC} $*" | tee -a "${LOG}"; }

detect_os() {
  [[ -f /etc/os-release ]] || fail "Cannot detect OS"
  # shellcheck disable=SC1091
  . /etc/os-release
  OS="${ID}"
  VERSION="${VERSION_ID}"
}

# Normalize version: 8.3 -> 83 for package names
normalize() {
  echo "${1//./}"
}

pkg_name() {
  local normalized
  normalized="$(normalize "${1}")"
  echo "lsphp${normalized}"
}

pkg_extensions() {
  local p
  p="$(pkg_name "${1}")"
  echo "${p}-common ${p}-mysql ${p}-curl ${p}-xml ${p}-zip ${p}-mbstring ${p}-intl ${p}-gd ${p}-opcache"
}

ensure_repo_debian() {
  if [[ ! -f /etc/apt/sources.list.d/lst_debian_repo.list ]] && \
     [[ ! -f /etc/apt/sources.list.d/lst_repo.list ]]; then
    ok "Adding OpenLiteSpeed repository..."
    curl -fsSL https://repo.litespeed.sh | bash >>"${LOG}" 2>&1 || \
      fail "Could not add OLS repo. Add it manually: https://openlitespeed.org/kb/install-open-litespeed/"
    apt-get update -y >>"${LOG}" 2>&1
  fi
}

ensure_repo_rhel() {
  if [[ ! -f /etc/yum.repos.d/litespeed.repo ]]; then
    ok "Adding OpenLiteSpeed repository..."
    curl -fsSL https://repo.litespeed.sh | bash >>"${LOG}" 2>&1 || \
      fail "Could not add OLS repo. Add it manually."
    dnf makecache >>"${LOG}" 2>&1 || true
  fi
}

install_version() {
  local ver="${1}"
  local p
  p="$(pkg_name "${ver}")"
  local exts
  exts="$(pkg_extensions "${ver}")"

  ok "Installing PHP ${ver} (OLS LSPHP handler: ${p})..."

  detect_os
  if [[ "${OS}" == "ubuntu" || "${OS}" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    ensure_repo_debian
    # shellcheck disable=SC2086
    apt-get install -y ${p} ${exts} >>"${LOG}" 2>&1 || fail "Package install failed for ${p}"
  elif [[ "${OS}" == "almalinux" || "${OS}" == "rocky" || "${OS}" == "centos" ]]; then
    ensure_repo_rhel
    # shellcheck disable=SC2086
    dnf install -y ${p} ${exts} >>"${LOG}" 2>&1 || fail "Package install failed for ${p}"
  else
    fail "Unsupported OS: ${OS}"
  fi

  local bin="${OLS_LSPHP_BASE}/${p}/bin/php"
  if [[ -x "${bin}" ]]; then
    ok "PHP ${ver} installed: $("${bin}" -r 'echo PHP_VERSION;')"
  else
    warn "Binary not found at ${bin} after install. Check package name and repo."
  fi
}

uninstall_version() {
  local ver="${1}"
  local p
  p="$(pkg_name "${ver}")"
  detect_os
  ok "Removing PHP ${ver} (${p})..."
  if [[ "${OS}" == "ubuntu" || "${OS}" == "debian" ]]; then
    apt-get remove -y "${p}" >>"${LOG}" 2>&1 || warn "Package not found: ${p}"
  else
    dnf remove -y "${p}" >>"${LOG}" 2>&1 || warn "Package not found: ${p}"
  fi
  ok "PHP ${ver} removed"
}

list_versions() {
  echo ""
  echo "Installed LSPHP handlers in ${OLS_LSPHP_BASE}:"
  echo "─────────────────────────────────────────────"
  printf "  %-10s %-12s %s\n" "Handler" "PHP Version" "Binary"
  echo "─────────────────────────────────────────────"

  if [[ ! -d "${OLS_LSPHP_BASE}" ]]; then
    echo "  OpenLiteSpeed not found at ${OLS_LSPHP_BASE}"
    return
  fi

  found=0
  for handler_dir in "${OLS_LSPHP_BASE}"/lsphp*/; do
    handler="$(basename "${handler_dir}")"
    bin="${handler_dir}bin/php"
    if [[ -x "${bin}" ]]; then
      phpver="$("${bin}" -r 'echo PHP_VERSION;' 2>/dev/null || echo '?')"
      printf "  %-10s %-12s %s\n" "${handler}" "${phpver}" "${bin}"
      found=1
    fi
  done

  [[ "${found}" -eq 0 ]] && echo "  No LSPHP handlers found"
  echo ""
}

set_default() {
  local ver="${1}"
  local p
  p="$(pkg_name "${ver}")"
  local bin="${OLS_LSPHP_BASE}/${p}/bin/php"

  [[ -x "${bin}" ]] || fail "PHP ${ver} not installed (expected at ${bin})"

  local conf="/usr/local/lsws/conf/httpd_config.conf"
  if [[ -f "${conf}" ]]; then
    ok "Updating default PHP in OLS config to ${p}"
    sed -i "s|lsphp[0-9][0-9]|${p}|g" "${conf}" 2>>"${LOG}" || warn "Could not auto-update httpd_config.conf — update manually"
    /usr/local/lsws/bin/lswsctrl restart >>"${LOG}" 2>&1 || warn "OLS restart failed — restart manually"
  else
    warn "OLS config not found at ${conf} — update default PHP handler manually"
  fi

  ok "Default set to PHP ${ver}"
}

show_status() {
  list_versions
  default_link="${OLS_LSPHP_BASE}/lsphp/bin/php"
  if [[ -L "${default_link}" ]]; then
    ok "Default symlink: ${default_link} -> $(readlink "${default_link}")"
  else
    warn "No default LSPHP symlink found at ${default_link}"
  fi
}

CMD="${1:-}"
case "${CMD}" in
  install)
    [[ -z "${2:-}" ]] && fail "Usage: $0 install <version> (e.g. 8.3)"
    install_version "${2}"
    ;;
  uninstall)
    [[ -z "${2:-}" ]] && fail "Usage: $0 uninstall <version>"
    uninstall_version "${2}"
    ;;
  list)
    list_versions
    ;;
  set-default)
    [[ -z "${2:-}" ]] && fail "Usage: $0 set-default <version>"
    set_default "${2}"
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: $0 <install|uninstall|list|set-default|status> [version]"
    exit 1
    ;;
esac
