#!/usr/bin/env bash
set -euo pipefail

USERNAME="${username:-${1:-}}"
if [[ -z "$USERNAME" ]]; then
  echo "username is required" >&2
  exit 1
fi

SRC="/home/$USERNAME"
DEST_DIR="/var/hspanel/backups"
mkdir -p "$DEST_DIR"
DEST="$DEST_DIR/${USERNAME}_$(date +%Y%m%d_%H%M%S).tar.gz"

tar -czf "$DEST" "$SRC"
echo "Backup created: $DEST"
