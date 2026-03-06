#!/bin/bash
###############################################################################
# HostingSignal — Ubuntu/Debian Package Setup
###############################################################################
set -e

log_info()  { echo -e "\033[0;32m[✓]\033[0m $1"; }
log_step()  { echo -e "\033[0;36m[→]\033[0m $1"; }
log_warn()  { echo -e "\033[0;33m[!]\033[0m $1"; }

cat << "EOF"
  _   _           _   _             _____ _                   _ 
 | | | |         | | (_)           / ____(_)                 | |
 | |_| | ___  ___| |_ _ _ __   __ | (___  _  __ _ _ __   __ _| |
 |  _  |/ _ \/ __| __| | '_ \ / _` \___ \| |/ _` | '_ \ / _` | |
 | | | | (_) \__ \ |_| | | | | (_| |___) | | (_| | | | | (_| | |
 \_| |_/\___/|___/\__|_|_| |_|\__, |____/|_|\__, |_| |_|\__,_|_|
                               __/ |         __/ |              
                              |___/         |___/               
EOF
echo ""
echo "================================================================="
echo "  HostingSignal - Next-Gen Web Hosting Control Panel Installer  "
echo "================================================================="
echo ""

export DEBIAN_FRONTEND=noninteractive

log_step "Updating package lists..."
apt-get update -y

# Core tools
log_step "Installing core tools..."
apt-get install -y curl wget git unzip tar software-properties-common gnupg2 \
    apt-transport-https ca-certificates lsb-release

# Python 3.10+
log_step "Installing Python..."
apt-get install -y python3 python3-pip python3-venv python3-dev

# Node.js 18 LTS
log_step "Installing Node.js 18..."
if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi
log_info "Node.js $(node -v)"

# OpenLiteSpeed
log_step "Installing OpenLiteSpeed..."
if ! command -v /usr/local/lsws/bin/lswsctrl &>/dev/null; then
    wget -qO - https://repo.litespeed.sh | bash
    apt-get install -y openlitespeed
    /usr/local/lsws/bin/lswsctrl start
fi
log_info "OpenLiteSpeed installed"

# PHP (lsphp 8.1 + 8.2 & PHP 8.2)
log_step "Installing PHP..."
export LC_ALL=C.UTF-8
if ! add-apt-repository ppa:ondrej/php -y; then
    log_warn "Failed to add PPA via add-apt-repository. Attempting manual curl method..."
    curl -sS https://packages.sury.org/php/apt.gpg | tee /etc/apt/trusted.gpg.d/php.gpg > /dev/null
    echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/php.list
fi
apt-get update -y
apt-get install -y lsphp81 lsphp81-common lsphp81-mysql lsphp81-curl lsphp81-json \
    lsphp82 lsphp82-common lsphp82-mysql lsphp82-curl 2>/dev/null || \
    apt-get install -y php8.2-fpm php8.2-mysql php8.2-curl php8.2-gd php8.2-mbstring php8.2-xml
log_info "PHP installed"

# MariaDB
log_step "Installing MariaDB..."
apt-get install -y mariadb-server mariadb-client
systemctl enable --now mariadb
log_info "MariaDB installed"

# PowerDNS
log_step "Installing PowerDNS..."
apt-get install -y pdns-server pdns-backend-mysql
systemctl enable pdns
log_info "PowerDNS installed"

# Postfix + Dovecot
log_step "Installing Mail Server..."
debconf-set-selections <<< "postfix postfix/mailname string $(hostname -f)"
debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
apt-get install -y postfix dovecot-core dovecot-imapd dovecot-pop3d opendkim opendkim-tools
systemctl enable postfix dovecot
log_info "Mail Server installed (Postfix + Dovecot)"

# Pure-FTPd
log_step "Installing FTP Server..."
apt-get install -y pure-ftpd
systemctl enable pure-ftpd
log_info "Pure-FTPd installed"

# Cache & Anti-Spam (CyberPanel parity)
log_step "Installing Redis, Memcached, & SpamAssassin..."
apt-get install -y redis-server memcached spamassassin spamc
systemctl enable --now redis-server memcached spamassassin
log_info "Caching & Anti-Spam tools installed"

# Certbot (Let's Encrypt)
log_step "Installing Certbot..."
apt-get install -y certbot
log_info "Certbot installed"

# Firewall
log_step "Configuring Firewall..."
apt-get install -y firewalld
systemctl enable --now firewalld
log_info "FirewallD installed"


# phpMyAdmin
log_step "Installing phpMyAdmin..."
PHPMYADMIN_DIR="/usr/local/lsws/phpmyadmin"
if [ ! -d "$PHPMYADMIN_DIR" ]; then
    mkdir -p "$PHPMYADMIN_DIR"
    wget -qO /tmp/phpmyadmin.tar.gz "https://files.phpmyadmin.net/phpMyAdmin/5.2.1/phpMyAdmin-5.2.1-all-languages.tar.gz"
    tar -xzf /tmp/phpmyadmin.tar.gz --strip-components=1 -C "$PHPMYADMIN_DIR"
    rm /tmp/phpmyadmin.tar.gz
fi
log_info "phpMyAdmin installed"

# SnappyMail (Webmail)
log_step "Installing SnappyMail..."
WEBMAIL_DIR="/usr/local/lsws/webmail"
if [ ! -d "$WEBMAIL_DIR" ]; then
    mkdir -p "$WEBMAIL_DIR"
    SNAPPY_VER=$(curl -s https://api.github.com/repos/the-djmaze/snappymail/releases/latest | grep tag_name | cut -d '"' -f 4 | tr -d v)
    wget -qO /tmp/snappymail.zip "https://github.com/the-djmaze/snappymail/releases/download/v${SNAPPY_VER}/snappymail-${SNAPPY_VER}.zip"
    unzip -q /tmp/snappymail.zip -d "$WEBMAIL_DIR"
    rm /tmp/snappymail.zip
fi
log_info "SnappyMail installed"

log_info "All Ubuntu packages installed successfully!"
