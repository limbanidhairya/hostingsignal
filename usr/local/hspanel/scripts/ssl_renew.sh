#!/usr/bin/env bash
set -euo pipefail

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot not found" >&2
  exit 1
fi

certbot renew --non-interactive || true
systemctl reload lsws || true

echo "SSL renewal task completed"
