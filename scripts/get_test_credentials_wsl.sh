#!/usr/bin/env bash
set -euo pipefail

# Prints current developer API test credentials and optionally verifies login.
#
# Usage:
#   bash scripts/get_test_credentials_wsl.sh [--verify]

ENV_FILE="/etc/hostingsignal/hostingsignal-devapi.env"
VERIFY=false

if [[ "${1:-}" == "--verify" ]]; then
  VERIFY=true
fi

get_env_value() {
  local key="$1"
  local default_value="$2"
  if [[ -f "$ENV_FILE" ]]; then
    local value
    value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d'=' -f2- || true)"
    if [[ -n "$value" ]]; then
      echo "$value"
      return
    fi
  fi
  echo "$default_value"
}

email="$(get_env_value HSDEV_DEFAULT_ADMIN_EMAIL admin@hostingsignal.local)"
username="$(get_env_value HSDEV_DEFAULT_ADMIN_USERNAME admin)"
password="$(get_env_value HSDEV_DEFAULT_ADMIN_PASSWORD Admin@123)"

cat <<EOF
HS-Panel Test Credentials
-------------------------
email:    ${email}
username: ${username}
password: ${password}
EOF

if [[ "$VERIFY" == "true" ]]; then
  python3 - <<PY
import json
import urllib.request

email = ${email@Q}
password = ${password@Q}

payload = json.dumps({"email": email, "password": password}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:2087/api/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print("login_check: success")
print("token_type:", data.get("token_type", ""))
print("expires_in:", data.get("expires_in", ""))
PY
fi
