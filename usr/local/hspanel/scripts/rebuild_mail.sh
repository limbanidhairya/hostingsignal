#!/usr/bin/env bash
set -euo pipefail

if command -v postmap >/dev/null 2>&1; then
  [[ -f /etc/postfix/virtual_domains ]] && postmap /etc/postfix/virtual_domains || true
  [[ -f /etc/postfix/virtual_mailboxes ]] && postmap /etc/postfix/virtual_mailboxes || true
fi

systemctl reload postfix || systemctl restart postfix
systemctl reload dovecot || systemctl restart dovecot

echo "Mail maps rebuilt and services reloaded"
