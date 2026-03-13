#!/usr/bin/env bash
set -euo pipefail

MODE=""
SERVICE_ID=""
CLIENT_ID=""
DOMAIN=""
PACKAGE_NAME=""
PLAN=""
REASON=""

for arg in "$@"; do
  case "$arg" in
    mode=*) MODE="${arg#mode=}" ;;
    service_id=*) SERVICE_ID="${arg#service_id=}" ;;
    client_id=*) CLIENT_ID="${arg#client_id=}" ;;
    domain=*) DOMAIN="${arg#domain=}" ;;
    package_name=*) PACKAGE_NAME="${arg#package_name=}" ;;
    plan=*) PLAN="${arg#plan=}" ;;
    reason=*) REASON="${arg#reason=}" ;;
  esac
done

if [[ -z "$MODE" || -z "$SERVICE_ID" ]]; then
  echo "missing required args: mode, service_id"
  exit 1
fi

STATE_DIR="/var/hspanel/userdata/whmcs_services"
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/${SERVICE_ID}.json"

if [[ -f "$STATE_FILE" ]]; then
  EXISTING=$(python3 - <<PY
import json
from pathlib import Path
p = Path("$STATE_FILE")
try:
    data = json.loads(p.read_text())
except Exception:
    data = {}
print(data.get("client_id", ""))
print(data.get("domain", ""))
print(data.get("package_name", ""))
print(data.get("plan", ""))
PY
)
  EXISTING_CLIENT_ID=$(echo "$EXISTING" | sed -n '1p')
  EXISTING_DOMAIN=$(echo "$EXISTING" | sed -n '2p')
  EXISTING_PACKAGE_NAME=$(echo "$EXISTING" | sed -n '3p')
  EXISTING_PLAN=$(echo "$EXISTING" | sed -n '4p')

  [[ -z "$CLIENT_ID" ]] && CLIENT_ID="$EXISTING_CLIENT_ID"
  [[ -z "$DOMAIN" ]] && DOMAIN="$EXISTING_DOMAIN"
  [[ -z "$PACKAGE_NAME" ]] && PACKAGE_NAME="$EXISTING_PACKAGE_NAME"
  [[ -z "$PLAN" ]] && PLAN="$EXISTING_PLAN"
fi

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

write_state() {
  local status="$1"
  local msg="$2"
  cat > "$STATE_FILE" <<EOF
{
  "service_id": "${SERVICE_ID}",
  "client_id": "${CLIENT_ID}",
  "domain": "${DOMAIN}",
  "package_name": "${PACKAGE_NAME}",
  "plan": "${PLAN}",
  "status": "${status}",
  "message": "${msg}",
  "updated_at": "$(now_utc)"
}
EOF
}

case "$MODE" in
  create)
    write_state "active" "Service provisioned"
    echo "Provisioned service ${SERVICE_ID} for ${DOMAIN}"
    ;;
  suspend)
    write_state "suspended" "${REASON:-Suspended by WHMCS}"
    echo "Suspended service ${SERVICE_ID}"
    ;;
  unsuspend)
    write_state "active" "Service unsuspended"
    echo "Unsuspended service ${SERVICE_ID}"
    ;;
  terminate)
    write_state "terminated" "${REASON:-Terminated by WHMCS}"
    echo "Terminated service ${SERVICE_ID}"
    ;;
  *)
    echo "unsupported mode: $MODE"
    exit 1
    ;;
esac
