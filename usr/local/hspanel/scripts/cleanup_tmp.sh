#!/usr/bin/env bash
set -euo pipefail

TARGETS=(/tmp /var/tmp)
MAX_AGE_DAYS="${max_age_days:-7}"

for t in "${TARGETS[@]}"; do
  [[ -d "$t" ]] || continue
  find "$t" -xdev -type f -mtime "+$MAX_AGE_DAYS" -delete 2>/dev/null || true
done

echo "Temporary cleanup completed"
