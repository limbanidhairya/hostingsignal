#!/usr/bin/env bash
set -euo pipefail

IP="${ip:-${1:-}}"
ACTION="${action:-deny}"
if [[ -z "$IP" ]]; then
  echo "ip is required" >&2
  exit 1
fi

if ! command -v csf >/dev/null 2>&1; then
  echo "csf not found" >&2
  exit 1
fi

case "$ACTION" in
  allow)
    csf -a "$IP" "HS-Panel allow"
    ;;
  remove)
    csf -dr "$IP" || true
    ;;
  deny|*)
    csf -d "$IP" "HS-Panel deny"
    ;;
esac

echo "IP action applied: $ACTION $IP"
