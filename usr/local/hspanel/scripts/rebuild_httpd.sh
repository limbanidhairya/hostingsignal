#!/usr/bin/env bash
set -euo pipefail

LSWS_CTRL="/usr/local/lsws/bin/lswsctrl"
if [[ -x "$LSWS_CTRL" ]]; then
  "$LSWS_CTRL" restart
  echo "OpenLiteSpeed configuration reloaded"
else
  echo "lswsctrl not found at $LSWS_CTRL" >&2
  exit 1
fi
