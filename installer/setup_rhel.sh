#!/bin/bash
###############################################################################
# HostingSignal — RHEL/AlmaLinux/CentOS Package Setup
###############################################################################
set -e

log_info()  { echo -e "\033[0;32m[✓]\033[0m $1"; }
log_step()  { echo -e "\033[0;34m[→]\033[0m $1"; }

log_step "Updating packages..."
dnf update -y
dnf install -y epel-release

# Core tools
log_step "Installing core tools..."
dnf install -y curl wget git unzip tar gcc make openssl-devel

# Python 3.10+
log_step "Installing Python..."
dnf install -y python3 python3-pip python3-devel

# Node.js 18 LTS
log_step "Installing Node.js 18..."
if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    dnf install -y nodejs
fi
log_info "Node.js $(node -v)"

# OpenLiteSpeed
log_step "Installing OpenLiteSpeed..."
if ! command -v /usr/local/lsws/bin/lswsctrl &>/dev/null; then
    rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.3-1.el8.noarch.rpm 2>/dev/null || true
    dnf install -y openlitespeed
    /usr/local/lsws/bin/lswsctrl start
fi
log_info "OpenLiteSpeed installed"

# PHP
log_step "Installing PHP..."
dnf install -y lsphp82 lsphp82-common lsphp82-mysqlnd lsphp82-process lsphp82-gd \
    lsphp81 lsphp81-common lsphp81-mysqlnd 2>/dev/null || \
    dnf install -y php php-fpm php-mysqlnd php-gd php-mbstring php-xml php-curl
log_info "PHP installed"

# MariaDB
log_step "Installing MariaDB..."
dnf install -y mariadb-server mariadb
systemctl enable --now mariadb
log_info "MariaDB installed"

# PowerDNS
log_step "Installing PowerDNS..."
dnf install -y pdns pdns-backend-mysql
systemctl enable pdns
log_info "PowerDNS installed"

# Postfix + Dovecot
log_step "Installing Mail Server..."
dnf install -y postfix dovecot opendkim opendkim-tools
systemctl enable postfix dovecot
log_info "Mail Server installed"

# Pure-FTPd
log_step "Installing FTP Server..."
dnf install -y pure-ftpd
systemctl enable pure-ftpd
log_info "Pure-FTPd installed"

# Certbot
log_step "Installing Certbot..."
dnf install -y certbot
log_info "Certbot installed"

# FirewallD
log_step "Configuring Firewall..."
dnf install -y firewalld
systemctl enable --now firewalld
log_info "FirewallD installed"

# Docker
log_step "Installing Docker..."
if ! command -v docker &>/dev/null; then
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo 2>/dev/null || true
    dnf install -y docker-ce docker-ce-cli containerd.io
    systemctl enable --now docker
fi
log_info "Docker installed"

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

# SnappyMail
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

log_info "All RHEL packages installed successfully!"
