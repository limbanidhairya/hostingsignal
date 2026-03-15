#!/usr/bin/env bash
set -euo pipefail

# Configure PowerDNS to run without conflicting with systemd-resolved in WSL.

PDNS_CONF="/etc/powerdns/pdns.conf"

if [[ ! -f "${PDNS_CONF}" ]]; then
  echo "PowerDNS config not found: ${PDNS_CONF}" >&2
  exit 1
fi

# Keep authoritative DNS reachable on localhost:5300 in WSL.
sed -i 's/^local-address=.*/local-address=127.0.0.1/' "${PDNS_CONF}" || true
if grep -q '^local-port=' "${PDNS_CONF}"; then
  sed -i 's/^local-port=.*/local-port=5300/' "${PDNS_CONF}"
else
  echo 'local-port=5300' >> "${PDNS_CONF}"
fi

if grep -q '^webserver=' "${PDNS_CONF}"; then
  sed -i 's/^webserver=.*/webserver=yes/' "${PDNS_CONF}"
else
  echo 'webserver=yes' >> "${PDNS_CONF}"
fi

if grep -q '^api=' "${PDNS_CONF}"; then
  sed -i 's/^api=.*/api=yes/' "${PDNS_CONF}"
else
  echo 'api=yes' >> "${PDNS_CONF}"
fi

if grep -q '^webserver-address=' "${PDNS_CONF}"; then
  sed -i 's/^webserver-address=.*/webserver-address=127.0.0.1/' "${PDNS_CONF}"
else
  echo 'webserver-address=127.0.0.1' >> "${PDNS_CONF}"
fi

if grep -q '^webserver-port=' "${PDNS_CONF}"; then
  sed -i 's/^webserver-port=.*/webserver-port=8053/' "${PDNS_CONF}"
else
  echo 'webserver-port=8053' >> "${PDNS_CONF}"
fi

if grep -q '^webserver-allow-from=' "${PDNS_CONF}"; then
  sed -i 's/^webserver-allow-from=.*/webserver-allow-from=127.0.0.1,::1/' "${PDNS_CONF}"
else
  echo 'webserver-allow-from=127.0.0.1,::1' >> "${PDNS_CONF}"
fi

systemctl restart pdns
systemctl is-active pdns

echo "PowerDNS WSL config applied (127.0.0.1:5300)"
