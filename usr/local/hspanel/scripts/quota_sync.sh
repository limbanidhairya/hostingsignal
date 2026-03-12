#!/usr/bin/env bash
set -euo pipefail

BASE="/var/hspanel/users"
[[ -d "$BASE" ]] || exit 0

while IFS= read -r -d '' dir; do
  user=$(basename "$dir")
  usage_kb=$(du -sk "$dir" 2>/dev/null | awk '{print $1}')
  echo "$user:$usage_kb"
done < <(find "$BASE" -mindepth 1 -maxdepth 1 -type d -print0)

echo "Quota sync completed"
