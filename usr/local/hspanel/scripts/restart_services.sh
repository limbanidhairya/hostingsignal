#!/usr/bin/env bash
set -euo pipefail

services=(lsws mariadb postfix dovecot pdns pure-ftpd)
for svc in "${services[@]}"; do
  systemctl restart "$svc" || true
  systemctl enable "$svc" || true
done

echo "Core services restarted"
