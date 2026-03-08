#!/bin/bash
###############################################################################
# HostingSignal Panel — PHP Version Manager
# Manages PHP installations, version switching, and extensions.
# Supports: PHP 7.4, 8.0, 8.1, 8.2, 8.3
# Works with both OpenLiteSpeed (lsphp) and Apache (php-fpm)
###############################################################################
set -euo pipefail

PHP_VERSIONS=("7.4" "8.0" "8.1" "8.2" "8.3")
LOG_FILE="/var/log/hostingsignal/php-manager.log"
WEB_SERVER=""  # openlitespeed | apache

# Detect web server
detect_webserver() {
    if [ -d "/usr/local/lsws" ]; then
        WEB_SERVER="openlitespeed"
    elif command -v apache2 &>/dev/null || command -v httpd &>/dev/null; then
        WEB_SERVER="apache"
    else
        echo "⚠️  No supported web server detected"
        WEB_SERVER="unknown"
    fi
}

# ── Install PHP Version ─────────────────────────────────────────────────────

install_php() {
    local VERSION="$1"
    echo "[+] Installing PHP $VERSION..."

    if [ "$WEB_SERVER" = "openlitespeed" ]; then
        local PKG="lsphp${VERSION//./}"
        apt-get install -y \
            "$PKG" \
            "${PKG}-common" \
            "${PKG}-mysql" \
            "${PKG}-curl" \
            "${PKG}-opcache" \
            "${PKG}-gd" \
            "${PKG}-imap" \
            "${PKG}-intl" \
            "${PKG}-json" 2>/dev/null || true
        echo "✅ lsphp${VERSION//./} installed"
    else
        # Apache / php-fpm
        add-apt-repository -y ppa:ondrej/php >> "$LOG_FILE" 2>&1 || true
        apt-get update -y >> "$LOG_FILE" 2>&1
        apt-get install -y \
            "php${VERSION}" \
            "php${VERSION}-fpm" \
            "php${VERSION}-cli" \
            "php${VERSION}-common" \
            "php${VERSION}-mysql" \
            "php${VERSION}-curl" \
            "php${VERSION}-gd" \
            "php${VERSION}-intl" \
            "php${VERSION}-zip" \
            "php${VERSION}-opcache" \
            "php${VERSION}-xml" \
            "php${VERSION}-mbstring" >> "$LOG_FILE" 2>&1
        systemctl enable "php${VERSION}-fpm" >> "$LOG_FILE" 2>&1
        systemctl start "php${VERSION}-fpm" >> "$LOG_FILE" 2>&1
        echo "✅ PHP $VERSION with php-fpm installed"
    fi
}

# ── Remove PHP Version ──────────────────────────────────────────────────────

remove_php() {
    local VERSION="$1"
    echo "[-] Removing PHP $VERSION..."

    if [ "$WEB_SERVER" = "openlitespeed" ]; then
        apt-get purge -y "lsphp${VERSION//./}"* >> "$LOG_FILE" 2>&1
    else
        systemctl stop "php${VERSION}-fpm" 2>/dev/null || true
        apt-get purge -y "php${VERSION}"* >> "$LOG_FILE" 2>&1
    fi
    echo "✅ PHP $VERSION removed"
}

# ── Switch PHP for a Website ────────────────────────────────────────────────

switch_php() {
    local DOMAIN="$1"
    local VERSION="$2"
    echo "[~] Switching $DOMAIN to PHP $VERSION..."

    if [ "$WEB_SERVER" = "openlitespeed" ]; then
        # Update OLS vhost to use different lsphp binary
        local VHOST_CONF="/usr/local/lsws/conf/vhosts/${DOMAIN}/vhconf.conf"
        if [ -f "$VHOST_CONF" ]; then
            sed -i "s|lsphp[0-9]*/bin/lsphp|lsphp${VERSION//./}/bin/lsphp|g" "$VHOST_CONF"
            /usr/local/lsws/bin/lswsctrl restart 2>/dev/null || true
            echo "✅ $DOMAIN switched to lsphp${VERSION//./}"
        else
            echo "⚠️  Vhost config not found: $VHOST_CONF"
        fi
    else
        # Update Apache to use different php-fpm socket
        local SITE_CONF="/etc/apache2/sites-available/${DOMAIN}.conf"
        if [ -f "$SITE_CONF" ]; then
            sed -i "s|php[0-9.]*-fpm.sock|php${VERSION}-fpm.sock|g" "$SITE_CONF"
            systemctl reload apache2
            echo "✅ $DOMAIN switched to PHP $VERSION-fpm"
        else
            echo "⚠️  Site config not found: $SITE_CONF"
        fi
    fi
}

# ── Install PHP Extension ───────────────────────────────────────────────────

install_extension() {
    local VERSION="$1"
    local EXT="$2"
    echo "[+] Installing php${VERSION}-${EXT}..."

    if [ "$WEB_SERVER" = "openlitespeed" ]; then
        apt-get install -y "lsphp${VERSION//./}-${EXT}" >> "$LOG_FILE" 2>&1
    else
        apt-get install -y "php${VERSION}-${EXT}" >> "$LOG_FILE" 2>&1
    fi
    echo "✅ Extension $EXT installed for PHP $VERSION"
}

# ── Remove PHP Extension ────────────────────────────────────────────────────

remove_extension() {
    local VERSION="$1"
    local EXT="$2"
    echo "[-] Removing php${VERSION}-${EXT}..."

    if [ "$WEB_SERVER" = "openlitespeed" ]; then
        apt-get purge -y "lsphp${VERSION//./}-${EXT}" >> "$LOG_FILE" 2>&1
    else
        apt-get purge -y "php${VERSION}-${EXT}" >> "$LOG_FILE" 2>&1
    fi
    echo "✅ Extension $EXT removed from PHP $VERSION"
}

# ── List Installed PHP Versions ──────────────────────────────────────────────

list_php() {
    echo "Installed PHP versions:"
    for v in "${PHP_VERSIONS[@]}"; do
        if [ "$WEB_SERVER" = "openlitespeed" ]; then
            if dpkg -l "lsphp${v//./}" &>/dev/null 2>&1; then
                echo "  ● PHP $v (lsphp${v//./}) — installed"
            fi
        else
            if dpkg -l "php${v}" &>/dev/null 2>&1; then
                local fpm_status
                fpm_status=$(systemctl is-active "php${v}-fpm" 2>/dev/null || echo "inactive")
                echo "  ● PHP $v (fpm: $fpm_status) — installed"
            fi
        fi
    done
}

# ── List Extensions for a PHP Version ────────────────────────────────────────

list_extensions() {
    local VERSION="$1"
    echo "Extensions for PHP $VERSION:"
    if [ "$WEB_SERVER" = "openlitespeed" ]; then
        dpkg -l "lsphp${VERSION//./}-*" 2>/dev/null | grep '^ii' | awk '{print "  •", $2}' || echo "  None"
    else
        dpkg -l "php${VERSION}-*" 2>/dev/null | grep '^ii' | awk '{print "  •", $2}' || echo "  None"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

detect_webserver
mkdir -p "$(dirname "$LOG_FILE")"

case "${1:-help}" in
    install)     install_php "$2" ;;
    remove)      remove_php "$2" ;;
    switch)      switch_php "$2" "$3" ;;
    ext-install) install_extension "$2" "$3" ;;
    ext-remove)  remove_extension "$2" "$3" ;;
    list)        list_php ;;
    extensions)  list_extensions "$2" ;;
    *)
        echo "Usage:"
        echo "  php-manager.sh install <version>"
        echo "  php-manager.sh remove <version>"
        echo "  php-manager.sh switch <domain> <version>"
        echo "  php-manager.sh ext-install <version> <extension>"
        echo "  php-manager.sh ext-remove <version> <extension>"
        echo "  php-manager.sh list"
        echo "  php-manager.sh extensions <version>"
        echo ""
        echo "Supported versions: ${PHP_VERSIONS[*]}"
        echo "Supported extensions: curl imagick gd mysqli pdo zip intl opcache redis"
        ;;
esac
