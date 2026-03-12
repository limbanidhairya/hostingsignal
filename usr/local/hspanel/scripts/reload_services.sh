#!/usr/bin/env bash
# reload_services.sh — HostingSignal service safe-reload
# Called by wrap_sysop C wrapper. Only services in ALLOWED list may be reloaded.

set -euo pipefail

SERVICE="${1:-}"

if [[ -z "${SERVICE}" ]]; then
    echo "Usage: $0 <lsws|mariadb|postfix|dovecot|pdns|pure-ftpd|csf|docker>"
    exit 1
fi

case "${SERVICE}" in
    lsws)
        echo "Reloading OpenLiteSpeed..."
        if [[ -x /usr/local/lsws/bin/lswsctrl ]]; then
            /usr/local/lsws/bin/lswsctrl restart
        else
            systemctl reload lsws
        fi
        ;;
    mariadb|mysql)
        echo "Reloading MariaDB/MySQL..."
        systemctl reload "${SERVICE}" 2>/dev/null || systemctl reload mariadb
        ;;
    postfix)
        echo "Checking Postfix config..."
        postfix check
        echo "Reloading Postfix..."
        postfix reload
        ;;
    dovecot)
        echo "Reloading Dovecot..."
        doveadm reload
        ;;
    pdns)
        echo "Reloading PowerDNS..."
        if command -v pdns_control >/dev/null 2>&1; then
            pdns_control cycle
        else
            systemctl reload pdns
        fi
        ;;
    pure-ftpd)
        echo "Reloading Pure-FTPd..."
        systemctl reload pure-ftpd
        ;;
    csf)
        echo "Reloading CSF firewall..."
        csf -r
        ;;
    docker)
        echo "Reloading Docker..."
        systemctl reload docker
        ;;
    *)
        echo "Unknown service: ${SERVICE}"
        echo "Allowed: lsws, mariadb, postfix, dovecot, pdns, pure-ftpd, csf, docker"
        exit 1
        ;;
esac

echo "Service '${SERVICE}' reloaded successfully"
exit 0
