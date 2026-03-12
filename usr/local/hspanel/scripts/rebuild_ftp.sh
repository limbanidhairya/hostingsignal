#!/usr/bin/env bash
set -euo pipefail

if command -v pure-pw >/dev/null 2>&1; then
  pure-pw mkdb /etc/pure-ftpd/pureftpd.pdb
fi

systemctl restart pure-ftpd

echo "Pure-FTPd database rebuilt and service restarted"
