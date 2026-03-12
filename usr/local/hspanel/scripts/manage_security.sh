#!/usr/bin/env bash
###############################################################################
# HostingSignal — Security Stack Manager
# Installs and manages CSF, ModSecurity (OLS), and ImunifyAV.
#
# Usage:
#   ./manage_security.sh install   <csf|modsecurity|imunifyav|all>
#   ./manage_security.sh status    <csf|modsecurity|imunifyav|all>
#   ./manage_security.sh csf-allow <ip>
#   ./manage_security.sh csf-deny  <ip>
#   ./manage_security.sh csf-unblock <ip>
#   ./manage_security.sh csf-enable
#   ./manage_security.sh csf-disable
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_ROOT="${SCRIPT_DIR}/../../../local/services"
DOWNLOADS="${LOCAL_ROOT}/downloads"
LOG="${SCRIPT_DIR}/../../logs/security.log"
mkdir -p "$(dirname "${LOG}")" "${DOWNLOADS}"

OS=""; VERSION=""
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[SEC]${NC} $*" | tee -a "${LOG}"; }
fail() { echo -e "${RED}[SEC][ERROR]${NC} $*" | tee -a "${LOG}"; exit 1; }
warn() { echo -e "${YELLOW}[SEC][WARN]${NC} $*" | tee -a "${LOG}"; }

detect_os() {
  [[ -f /etc/os-release ]] || fail "Cannot detect OS"
  # shellcheck disable=SC1091
  . /etc/os-release
  OS="${ID}"; VERSION="${VERSION_ID}"
}

validate_ip() {
  local ip="${1}"
  if [[ ! "${ip}" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(/[0-9]{1,2})?$ ]] && \
     [[ ! "${ip}" =~ ^[0-9a-fA-F:]+(/[0-9]{1,3})?$ ]]; then
    fail "Invalid IP address: ${ip}"
  fi
}

install_csf() {
  ok "Installing ConfigServer Firewall (CSF)..."

  if command -v csf >/dev/null 2>&1; then
    ok "CSF already installed at $(command -v csf)"
    return
  fi

  local tarball="${DOWNLOADS}/csf.tgz"
  if [[ ! -f "${tarball}" ]]; then
    ok "Downloading CSF..."
    curl -fL --retry 3 -o "${tarball}" "https://download.configserver.com/csf.tgz" >>"${LOG}" 2>&1 || \
      fail "CSF download failed"
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  tar -xzf "${tarball}" -C "${tmpdir}" >>"${LOG}" 2>&1

  detect_os
  if [[ "${OS}" == "ubuntu" || "${OS}" == "debian" ]]; then
    apt-get install -y libwww-perl liblwp-protocol-https-perl libgd-graph-perl >>"${LOG}" 2>&1 || true
  else
    dnf install -y perl perl-libwww-perl perl-LWP-Protocol-https >>"${LOG}" 2>&1 || true
  fi

  bash "${tmpdir}/csf/install.sh" >>"${LOG}" 2>&1
  rm -rf "${tmpdir}"

  ok "CSF installed"
  warn "CSF is in TESTING mode. After confirming remote access works, run: csf -e"
}

install_modsecurity() {
  ok "Installing ModSecurity with OWASP CRS for OpenLiteSpeed..."

  detect_os
  local pkg_installed=false

  if [[ "${OS}" == "ubuntu" || "${OS}" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y libapache2-mod-security2 modsecurity-crs >>"${LOG}" 2>&1 && pkg_installed=true || true
    if [[ "${pkg_installed}" == "false" ]]; then
      apt-get install -y modsecurity-crs >>"${LOG}" 2>&1 || warn "modsecurity-crs package not available, will use CRS download"
    fi
  else
    dnf install -y mod_security mod_security_crs >>"${LOG}" 2>&1 && pkg_installed=true || true
  fi

  local crs_zip="${DOWNLOADS}/owasp-crs-main.zip"
  if [[ ! -f "${crs_zip}" ]]; then
    ok "Downloading OWASP CRS..."
    curl -fL --retry 3 -o "${crs_zip}" \
      "https://github.com/coreruleset/coreruleset/archive/refs/heads/main.zip" >>"${LOG}" 2>&1 || \
      warn "OWASP CRS download failed — install manually from https://coreruleset.org"
  fi

  local crs_target="/etc/modsecurity/crs"
  if [[ -f "${crs_zip}" ]] && [[ ! -d "${crs_target}" ]]; then
    mkdir -p "${crs_target}"
    unzip -o "${crs_zip}" -d "${crs_target}" >>"${LOG}" 2>&1 || warn "Could not extract OWASP CRS"
    ok "OWASP CRS extracted to ${crs_target}"
  fi

  ok "ModSecurity setup completed"
  warn "Enable ModSecurity in OLS admin: Security -> Web Application Firewall -> Enable"
}

install_imunifyav() {
  ok "Installing ImunifyAV..."

  if command -v imunify-antivirus >/dev/null 2>&1 || command -v imunifyav >/dev/null 2>&1; then
    ok "ImunifyAV already installed"
    return
  fi

  local installer="${DOWNLOADS}/imunifyav-install.sh"
  if [[ ! -f "${installer}" ]]; then
    ok "Downloading ImunifyAV installer..."
    curl -fL --retry 3 -o "${installer}" \
      "https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh" >>"${LOG}" 2>&1 || \
      fail "ImunifyAV installer download failed"
  fi

  chmod +x "${installer}"
  bash "${installer}" >>"${LOG}" 2>&1 || fail "ImunifyAV installation failed"
  ok "ImunifyAV installed"
}

status_all() {
  echo ""
  echo "────────────────────────────────────────"
  echo " Security Stack Status"
  echo "────────────────────────────────────────"

  # CSF
  if command -v csf >/dev/null 2>&1; then
    echo -e "  ${GREEN}[CSF    ]${NC} Installed"
    if [[ -f /etc/csf/csf.conf ]]; then
      if grep -q 'TESTING = "1"' /etc/csf/csf.conf 2>/dev/null; then
        echo -e "  ${YELLOW}[CSF    ]${NC} Mode: TESTING (not enforcing - run: csf -e)"
      else
        echo -e "  ${GREEN}[CSF    ]${NC} Mode: LIVE (enforcing)"
      fi
    fi
  else
    echo -e "  ${RED}[CSF    ]${NC} Not installed. Run: $0 install csf"
  fi

  # ModSecurity
  MOD_FOUND=false
  for p in /etc/modsecurity /usr/share/modsecurity-crs /etc/modsec; do
    if [[ -d "${p}" ]]; then
      echo -e "  ${GREEN}[MODSEC ]${NC} Found at ${p}"
      MOD_FOUND=true; break
    fi
  done
  [[ "${MOD_FOUND}" == "false" ]] && echo -e "  ${RED}[MODSEC ]${NC} Not found. Run: $0 install modsecurity"

  # ImunifyAV
  if command -v imunify-antivirus >/dev/null 2>&1 || command -v imunifyav >/dev/null 2>&1; then
    echo -e "  ${GREEN}[IMUNIFY]${NC} Installed"
  else
    echo -e "  ${YELLOW}[IMUNIFY]${NC} Not installed (optional). Run: $0 install imunifyav"
  fi

  echo ""
}

CMD="${1:-}"
case "${CMD}" in
  install)
    TARGET="${2:-all}"
    [[ "${EUID}" -ne 0 ]] && fail "Run as root"
    case "${TARGET}" in
      csf)          install_csf ;;
      modsecurity)  install_modsecurity ;;
      imunifyav)    install_imunifyav ;;
      all)
        install_csf
        install_modsecurity
        install_imunifyav
        ;;
      *) fail "Unknown target: ${TARGET}. Use: csf|modsecurity|imunifyav|all" ;;
    esac
    ;;
  status)
    status_all
    ;;
  csf-allow)
    [[ -z "${2:-}" ]] && fail "Usage: $0 csf-allow <ip>"
    validate_ip "${2}"
    command -v csf >/dev/null 2>&1 || fail "CSF not installed"
    csf -a "${2}" | tee -a "${LOG}"
    ;;
  csf-deny)
    [[ -z "${2:-}" ]] && fail "Usage: $0 csf-deny <ip>"
    validate_ip "${2}"
    command -v csf >/dev/null 2>&1 || fail "CSF not installed"
    csf -d "${2}" | tee -a "${LOG}"
    ;;
  csf-unblock)
    [[ -z "${2:-}" ]] && fail "Usage: $0 csf-unblock <ip>"
    validate_ip "${2}"
    command -v csf >/dev/null 2>&1 || fail "CSF not installed"
    csf -dr "${2}" | tee -a "${LOG}"
    csf -ar "${2}" | tee -a "${LOG}"
    ;;
  csf-enable)
    command -v csf >/dev/null 2>&1 || fail "CSF not installed"
    csf -e | tee -a "${LOG}"
    ok "CSF enabled (testing mode off)"
    ;;
  csf-disable)
    command -v csf >/dev/null 2>&1 || fail "CSF not installed"
    csf -x | tee -a "${LOG}"
    warn "CSF disabled"
    ;;
  *)
    echo "Usage: $0 <install|status|csf-allow|csf-deny|csf-unblock|csf-enable|csf-disable> [args...]"
    exit 1
    ;;
esac
