#!/usr/bin/env bash
# HS-Panel Installer — Rollback Manager
# Tracks installed services and restores clean state on failure.

ROLLBACK_MANIFEST="${ROLLBACK_MANIFEST:-/var/log/hspanel_rollback_manifest.txt}"
ROLLBACK_LOG="${ROLLBACK_LOG:-/var/log/hspanel_rollback.log}"

# Internal stack of rollback actions (command strings)
declare -a _ROLLBACK_STACK=()

# ── Registration API ──────────────────────────────────────────────────────────
# register_rollback "command to run on rollback"
register_rollback() {
  _ROLLBACK_STACK+=("$*")
  echo "$*" >> "$ROLLBACK_MANIFEST" 2>/dev/null || true
}

# Mark a service as successfully installed
record_installed() {
  local svc="$1"
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$ts] INSTALLED $svc" >> "$ROLLBACK_MANIFEST"
  log_rollback "Recorded install: $svc"
}

# ── Execution ─────────────────────────────────────────────────────────────────
run_rollback() {
  local reason="${1:-unknown failure}"
  local ts
  ts="$(date '+%Y%m%d_%H%M%S')"
  local report="/root/hspanel_install_issues_${ts}.txt"

  log_rollback "━━━  ROLLBACK INITIATED  ━━━  reason: $reason"
  echo "HS-Panel rollback report — $ts" > "$report"
  echo "Reason: $reason"               >> "$report"
  echo ""                              >> "$report"

  # Execute rollback stack in reverse order
  local i
  for (( i=${#_ROLLBACK_STACK[@]}-1; i>=0; i-- )); do
    local cmd="${_ROLLBACK_STACK[$i]}"
    log_rollback "Running rollback: $cmd"
    echo "  - $cmd" >> "$report"
    eval "$cmd" >> "$ROLLBACK_LOG" 2>&1 || log_rollback "  ↳ rollback step failed (non-fatal): $cmd"
  done

  log_rollback "Rollback complete. Report saved to: $report"
  echo ""
  echo "Rollback log:  $ROLLBACK_LOG"
  echo "Issue report:  $report"
  echo "Install log:   $HSPANEL_LOG_FILE"
}

# ── Automatic trap ────────────────────────────────────────────────────────────
# Call this from the main orchestrator to auto-rollback on ERR:
#   trap 'on_install_error $? "$BASH_COMMAND" $LINENO' ERR
on_install_error() {
  local code="$1" cmd="$2" line="$3"
  log_error "Installation failed at line $line: '$cmd' (exit $code)"
  run_rollback "exit $code at line $line: $cmd"
  exit "$code"
}

# ── Pre-built rollback helpers ────────────────────────────────────────────────
rollback_remove_pkg_debian() {
  local pkg="$1"
  register_rollback "DEBIAN_FRONTEND=noninteractive apt-get remove -y --purge $pkg 2>/dev/null || true"
}

rollback_remove_pkg_rhel() {
  local pkg="$1"
  register_rollback "dnf remove -y $pkg 2>/dev/null || true"
}

rollback_stop_service() {
  local svc="$1"
  register_rollback "systemctl stop $svc 2>/dev/null; systemctl disable $svc 2>/dev/null || true"
}

rollback_remove_dir() {
  local dir="$1"
  register_rollback "rm -rf '$dir' 2>/dev/null || true"
}

rollback_restore_file() {
  local original="$1" backup="$2"
  register_rollback "[[ -f '$backup' ]] && cp '$backup' '$original' || true"
}
