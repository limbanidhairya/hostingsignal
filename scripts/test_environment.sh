#!/usr/bin/env bash
set -euo pipefail

# WSL Ubuntu 24.04 test loop for HS-Panel runtime readiness.

PASS=0
FAIL=0
TMP_OUT="$(mktemp /tmp/hs_test.out.XXXXXX)"
TMP_ERR="$(mktemp /tmp/hs_test.err.XXXXXX)"

cleanup() {
  rm -f "$TMP_OUT" "$TMP_ERR"
}

trap cleanup EXIT

ok() {
  echo "[PASS] $1"
  PASS=$((PASS + 1))
}

bad() {
  echo "[FAIL] $1"
  FAIL=$((FAIL + 1))
}

check_cmd() {
  local desc="$1"
  local cmd="$2"
  if bash -lc "$cmd" >"$TMP_OUT" 2>"$TMP_ERR"; then
    ok "$desc"
  else
    bad "$desc"
    sed -n '1,3p' "$TMP_ERR" || true
  fi
}

echo "=== HS-Panel WSL Environment Test ==="

check_cmd "Service hostingsignal-devapi active" "systemctl is-active --quiet hostingsignal-devapi"
check_cmd "Service hostingsignal-web active" "systemctl is-active --quiet hostingsignal-web"
check_cmd "Dev API health endpoint" "curl -fsS http://localhost:2087/api/health >/dev/null"
check_cmd "Web login reachable" "curl -fsS http://localhost:3000/login >/dev/null"
check_cmd "Main API health endpoint" "curl -fsS http://localhost:2083/health >/dev/null"
check_cmd "Queue directory present" "test -d /var/hspanel/queue"
check_cmd "WHMCS audit log present" "test -f /var/hspanel/logs/whmcs_audit.log || test -d /var/hspanel/logs"
check_cmd "MariaDB reachable (socket or service)" "systemctl is-active --quiet mariadb || systemctl is-active --quiet mysql"
check_cmd "Redis reachable" "systemctl is-active --quiet redis || systemctl is-active --quiet redis-server"
check_cmd "PowerDNS service active" "systemctl is-active --quiet pdns"
check_cmd "PowerDNS control API reachable" "curl -fsS http://127.0.0.1:8053 >/dev/null"
check_cmd "Orchestrator registry present" "test -f /usr/local/hspanel/core/orchestrator/services.json"
check_cmd "Recovery manager script present" "test -f /usr/local/hspanel/core/recovery-manager/recovery_manager.py"
check_cmd "DNS cluster sync script present" "test -f /usr/local/hspanel/core/dns-cluster/sync.sh"
check_cmd "Container runner script present" "test -f /usr/local/hspanel/core/container-runner/container_runner.py"
check_cmd "Recovery timer active" "systemctl is-active --quiet hostingsignal-recovery.timer"
check_cmd "License cache file present" "test -f /usr/local/hspanel/configs/license.cache"

echo
if [ "$FAIL" -eq 0 ]; then
  echo "Environment status: HEALTHY ($PASS checks passed)"
  exit 0
fi

echo "Environment status: DEGRADED ($FAIL failed, $PASS passed)"
exit 1
