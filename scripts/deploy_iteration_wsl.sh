#!/usr/bin/env bash
set -euo pipefail

# Deploys current iteration files from repo to /usr/local/hspanel in WSL,
# rebuilds/restarts required services, and runs verification checks.
#
# Usage:
#   sudo bash scripts/deploy_iteration_wsl.sh
#
# Optional auth vars for preflight verification:
#   HSDEV_ADMIN_EMAIL=admin@hostingsignal.local
#   HSDEV_ADMIN_PASSWORD=Admin@123

SRC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST_ROOT="/usr/local/hspanel"

HSDEV_ADMIN_EMAIL="${HSDEV_ADMIN_EMAIL:-admin@hostingsignal.local}"
HSDEV_ADMIN_PASSWORD="${HSDEV_ADMIN_PASSWORD:-Admin@123}"
BUILD_OUT="$(mktemp /tmp/hs_web_build.out.XXXXXX)"
BUILD_ERR="$(mktemp /tmp/hs_web_build.err.XXXXXX)"

cleanup() {
  rm -f "$BUILD_OUT" "$BUILD_ERR"
}

trap cleanup EXIT

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (use sudo)." >&2
  exit 1
fi

if [[ ! -d "${DST_ROOT}" ]]; then
  echo "Destination root not found: ${DST_ROOT}" >&2
  exit 1
fi

copy_file() {
  local rel="$1"
  local src="${SRC_ROOT}/${rel}"
  local dst="${DST_ROOT}/${rel}"
  if [[ ! -f "${src}" ]]; then
    echo "Missing source file: ${src}" >&2
    exit 1
  fi
  mkdir -p "$(dirname "${dst}")"
  install -m 0644 "${src}" "${dst}"
  echo "copied ${rel}"
}

copy_exec() {
  local rel="$1"
  local src="${SRC_ROOT}/${rel}"
  local dst="${DST_ROOT}/${rel}"
  if [[ ! -f "${src}" ]]; then
    echo "Missing source file: ${src}" >&2
    exit 1
  fi
  mkdir -p "$(dirname "${dst}")"
  install -m 0755 "${src}" "${dst}"
  echo "copied ${rel} (exec)"
}

wait_http() {
  local url="$1"
  local attempts="${2:-20}"
  local sleep_seconds="${3:-1}"
  local i
  for i in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  return 1
}

echo "==> Deploying iteration files"
copy_exec "core/container-runner/container_runner.py"
copy_exec "core/dns-cluster/sync.sh"
copy_file "core/container-runner/README.md"

copy_file "developer-panel/api/main.py"
copy_file "developer-panel/api/system.py"
copy_file "developer-panel/api/containers.py"
copy_file "developer-panel/api/config.py"
copy_file "developer-panel/web/src/app/page.js"

copy_file "cli/hsctl.py"
copy_exec "scripts/test_environment.sh"
copy_exec "scripts/deploy_iteration_wsl.sh"
copy_exec "scripts/fix_container_runtime_permissions_wsl.sh"

# Ensure hsctl is executable from install tree.
chmod +x "${DST_ROOT}/cli/hsctl.py"

echo "==> Restarting dev API"
systemctl restart hostingsignal-devapi
systemctl is-active --quiet hostingsignal-devapi
wait_http "http://127.0.0.1:2087/api/health" 30 1 || {
  echo "Dev API health endpoint did not become ready in time" >&2
  exit 1
}

echo "==> Rebuilding and restarting web"
cd "${DST_ROOT}/developer-panel/web"
npm run build >"$BUILD_OUT" 2>"$BUILD_ERR" || {
  echo "Web build failed" >&2
  sed -n '1,80p' "$BUILD_ERR" >&2 || true
  exit 1
}
systemctl restart hostingsignal-web
systemctl is-active --quiet hostingsignal-web
wait_http "http://127.0.0.1:3000/login" 45 1 || {
  echo "Web login endpoint did not become ready in time" >&2
  exit 1
}

echo "==> Runtime health checks"
curl -fsS http://127.0.0.1:2087/api/health >/dev/null
curl -fsS http://127.0.0.1:3000/login >/dev/null

echo "==> Preflight + container status check"
python3 - <<'PY'
import json
import os
import sys
import urllib.request

base = "http://127.0.0.1:2087"
email = os.environ.get("HSDEV_ADMIN_EMAIL", "admin@hostingsignal.local")
password = os.environ.get("HSDEV_ADMIN_PASSWORD", "Admin@123")

try:
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        token = json.loads(resp.read().decode("utf-8")).get("access_token", "")

    if not token:
        print("preflight-check: missing token", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    preflight_req = urllib.request.Request(f"{base}/api/system/preflight", headers=headers, method="GET")
    with urllib.request.urlopen(preflight_req, timeout=10) as resp:
        preflight = json.loads(resp.read().decode("utf-8"))

    runtime_req = urllib.request.Request(f"{base}/api/containers/status", headers=headers, method="GET")
    with urllib.request.urlopen(runtime_req, timeout=10) as resp:
        runtime = json.loads(resp.read().decode("utf-8"))

    report = preflight.get("report", {})
    runtime_data = runtime.get("data", {})
    print(json.dumps({
        "critical_failures": report.get("critical_failures"),
        "warning_count": report.get("warning_count"),
        "container_runtime": runtime_data,
    }, indent=2))
except Exception as exc:
    print(f"preflight-check failed: {exc}", file=sys.stderr)
    sys.exit(1)
PY

echo "==> WSL environment test"
"${DST_ROOT}/scripts/test_environment.sh"

echo "Deployment + verification complete"
