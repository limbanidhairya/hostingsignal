#!/usr/bin/env bash
# HS-Panel Installer — Logger
# Provides colored output, step tracking, and log file management.

HSPANEL_LOG_FILE="${HSPANEL_LOG_FILE:-/var/log/hspanel_install.log}"
HSPANEL_ROLLBACK_LOG="${HSPANEL_ROLLBACK_LOG:-/var/log/hspanel_rollback.log}"

# ── Colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_RESET="\033[0m"
  C_BOLD="\033[1m"
  C_DIM="\033[2m"
  C_GREEN="\033[0;32m"
  C_BGREEN="\033[1;32m"
  C_YELLOW="\033[0;33m"
  C_BYELLOW="\033[1;33m"
  C_RED="\033[0;31m"
  C_BRED="\033[1;31m"
  C_CYAN="\033[0;36m"
  C_BCYAN="\033[1;36m"
  C_BLUE="\033[0;34m"
  C_MAGENTA="\033[0;35m"
  C_WHITE="\033[1;37m"
else
  C_RESET="" C_BOLD="" C_DIM="" C_GREEN="" C_BGREEN=""
  C_YELLOW="" C_BYELLOW="" C_RED="" C_BRED="" C_CYAN=""
  C_BCYAN="" C_BLUE="" C_MAGENTA="" C_WHITE=""
fi

# ── Internal helpers ──────────────────────────────────────────────────────────
_ts() { date '+%Y-%m-%d %H:%M:%S'; }

_log_raw() {
  local level="$1"; shift
  local msg="$*"
  local ts
  ts="$(_ts)"
  mkdir -p "$(dirname "$HSPANEL_LOG_FILE")" 2>/dev/null || true
  echo "[$ts] [$level] $msg" >> "$HSPANEL_LOG_FILE"
}

# ── Public API ────────────────────────────────────────────────────────────────
log_info() {
  echo -e "${C_CYAN}  ➜  ${C_RESET}$*"
  _log_raw "INFO " "$*"
}

log_success() {
  echo -e "${C_BGREEN}  ✔  ${C_RESET}$*"
  _log_raw "OK   " "$*"
}

log_warning() {
  echo -e "${C_BYELLOW}  ⚠  ${C_RESET}$*"
  _log_raw "WARN " "$*"
}

log_error() {
  echo -e "${C_BRED}  ✖  ${C_RESET}$*" >&2
  _log_raw "ERR  " "$*"
}

log_step() {
  local step="$1"; shift
  echo ""
  echo -e "${C_BOLD}${C_BCYAN}━━━  STEP ${step}  ━━━  ${*}  ${C_RESET}"
  echo ""
  _log_raw "STEP " "[$step] $*"
}

log_section() {
  echo ""
  echo -e "${C_BOLD}${C_WHITE}  ┌──────────────────────────────────────────┐${C_RESET}"
  printf "${C_BOLD}${C_WHITE}  │  %-42s│${C_RESET}\n" "$*"
  echo -e "${C_BOLD}${C_WHITE}  └──────────────────────────────────────────┘${C_RESET}"
  echo ""
  _log_raw "SECT " "$*"
}

log_divider() {
  echo -e "${C_DIM}  ────────────────────────────────────────────────${C_RESET}"
}

log_kv() {
  local key="$1"; local val="$2"
  printf "  ${C_DIM}%-26s${C_RESET}  ${C_WHITE}%s${C_RESET}\n" "$key" "$val"
}

log_rollback() {
  local msg="$*"
  local ts
  ts="$(_ts)"
  mkdir -p "$(dirname "$HSPANEL_ROLLBACK_LOG")" 2>/dev/null || true
  echo "[$ts] $msg" | tee -a "$HSPANEL_ROLLBACK_LOG" >&2
  _log_raw "ROLL " "$msg"
}

# Progress bar — usage: progress_bar <current> <total> [label]
progress_bar() {
  local current="$1" total="$2" label="${3:-}"
  local width=40
  local filled=$(( current * width / total ))
  local empty=$(( width - filled ))
  local bar=""
  local i
  for (( i=0; i<filled; i++ )); do bar+="█"; done
  for (( i=0; i<empty;  i++ )); do bar+="░"; done
  local pct=$(( current * 100 / total ))
  printf "\r  ${C_CYAN}[${C_BGREEN}%s${C_CYAN}]${C_RESET} %3d%%  %s" "$bar" "$pct" "$label"
  if [[ "$current" -eq "$total" ]]; then echo ""; fi
}
