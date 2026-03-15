#!/usr/bin/env bash
set -euo pipefail

# Applies generated HSDEV production env to an existing hostingsignal-devapi service
# using a systemd drop-in override in WSL/Linux.
#
# Usage:
#   sudo bash scripts/apply_devapi_production_env_wsl.sh [env_file]

ENV_SOURCE="${1:-deployment/hostingsignal-devapi.production.env}"
ENV_TARGET_DIR="/etc/hostingsignal"
ENV_TARGET_FILE="${ENV_TARGET_DIR}/hostingsignal-devapi.env"
OVERRIDE_DIR="/etc/systemd/system/hostingsignal-devapi.service.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/override.conf"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (use sudo)." >&2
  exit 1
fi

if [[ ! -f "${ENV_SOURCE}" ]]; then
  echo "Env file not found: ${ENV_SOURCE}" >&2
  exit 1
fi

if grep -Eq 'CHANGE_DB_PASSWORD|CHANGE_LICENSE_API_KEY' "${ENV_SOURCE}"; then
  echo "Refusing to apply env file with unresolved placeholders." >&2
  echo "Please replace CHANGE_DB_PASSWORD and CHANGE_LICENSE_API_KEY first." >&2
  exit 1
fi

mkdir -p "${ENV_TARGET_DIR}"
install -m 600 "${ENV_SOURCE}" "${ENV_TARGET_FILE}"

mkdir -p "${OVERRIDE_DIR}"
cat >"${OVERRIDE_FILE}" <<EOF
[Service]
EnvironmentFile=-${ENV_TARGET_FILE}
EOF

systemctl daemon-reload
systemctl restart hostingsignal-devapi

if ! systemctl is-active --quiet hostingsignal-devapi; then
  echo "hostingsignal-devapi failed to start after env apply." >&2
  systemctl status --no-pager hostingsignal-devapi || true
  exit 1
fi

echo "Applied production env file to hostingsignal-devapi."
echo "Active unit override: ${OVERRIDE_FILE}"

echo "Health check:"
curl -fsS http://127.0.0.1:2087/api/health | sed -n '1,3p'

echo
echo "Next: login and verify /api/system/preflight critical_failures count drops."
