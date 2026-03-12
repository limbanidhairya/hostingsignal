#!/usr/bin/env bash
set -euo pipefail

if command -v systemctl >/dev/null 2>&1; then
  systemctl reload pdns || systemctl restart pdns
  echo "PowerDNS reloaded"
else
  echo "systemctl not available" >&2
  exit 1
fi
