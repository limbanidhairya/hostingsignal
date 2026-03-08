#!/bin/bash
###############################################################################
# HostingSignal Panel — Production Installer
# One-command installation:
#   bash <(curl -sSL https://mirror.hostingsignal.in/install.sh)
#
# Supports: Ubuntu 22+, Ubuntu 24+, Debian 12, AlmaLinux 9
###############################################################################
set -euo pipefail

# ── Variables ────────────────────────────────────────────────────────────────

INSTALL_DIR="/usr/local/hostingsignal"
CONFIG_DIR="/etc/hostingsignal"
LOG_DIR="/var/log/hostingsignal"
LOG_FILE="/var/log/hostingsignal-install.log"
REPO_URL="https://github.com/limbanidhairya/hostingsignal.git"
PANEL_VERSION="1.0.0"

# ── UI Helpers ───────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"; }
log_step()  { echo -e "${CYAN}[→]${NC} $1" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"; }
log_err()   { echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }

banner() {
    echo -e "${CYAN}"
    cat << 'BANNER'
  _   _           _   _             _____ _                   _ 
 | | | |         | | (_)           / ____(_)                 | |
 | |_| | ___  ___| |_ _ _ __   __ | (___  _  __ _ _ __   __ _| |
 |  _  |/ _ \/ __| __| | '_ \ / _` \___ \| |/ _` | '_ \ / _` | |
 | | | | (_) \__ \ |_| | | | | (_| |___) | | (_| | | | | (_| | |
 \_| |_/\___/|___/\__|_|_| |_|\__, |____/|_|\__, |_| |_|\__,_|_|
                               __/ |         __/ |              
                              |___/         |___/               
BANNER
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  HostingSignal Panel v${PANEL_VERSION} — Production Installer"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

# ── Pre-flight Checks ───────────────────────────────────────────────────────

preflight() {
    # Root check
    if [ "$(id -u)" != "0" ]; then
        log_err "This installer must be run as root. Use: sudo bash install.sh"
    fi

    # Create log file
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "HostingSignal Installation — $(date)" > "$LOG_FILE"

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$ID"
        OS_VERSION="$VERSION_ID"
        OS_PRETTY="$PRETTY_NAME"
    else
        log_err "Cannot detect OS. /etc/os-release not found."
    fi

    log_step "Detected OS: $OS_PRETTY"

    # Validate supported OS
    case "$OS_NAME" in
        ubuntu)
            if [[ "$OS_VERSION" != "22.04" && "$OS_VERSION" != "24.04" && ! "$OS_VERSION" > "22" ]]; then
                log_err "Unsupported Ubuntu version: $OS_VERSION. Requires 22.04 or 24.04."
            fi
            PKG_MANAGER="apt"
            ;;
        debian)
            if [[ "${OS_VERSION%%.*}" -lt 12 ]]; then
                log_err "Unsupported Debian version: $OS_VERSION. Requires 12+."
            fi
            PKG_MANAGER="apt"
            ;;
        almalinux|rocky|centos)
            if [[ "${OS_VERSION%%.*}" -lt 9 ]]; then
                log_err "Unsupported AlmaLinux version: $OS_VERSION. Requires 9+."
            fi
            PKG_MANAGER="dnf"
            ;;
        *)
            log_err "Unsupported OS: $OS_NAME. Supported: Ubuntu 22+, Debian 12+, AlmaLinux 9+"
            ;;
    esac

    # Check minimum RAM (1GB)
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 900 ]; then
        log_warn "Low RAM detected: ${TOTAL_RAM}MB. Minimum recommended: 1024MB."
    fi

    # Check minimum disk (20GB)
    TOTAL_DISK=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
    if [ "$TOTAL_DISK" -lt 15 ]; then
        log_warn "Low disk space: ${TOTAL_DISK}GB available. Minimum recommended: 20GB."
    fi

    log_info "Pre-flight checks passed"
}

# ── Install Dependencies (Debian/Ubuntu) ────────────────────────────────────

install_deps_apt() {
    log_step "Updating system packages..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y >> "$LOG_FILE" 2>&1
    apt-get upgrade -y >> "$LOG_FILE" 2>&1

    log_step "Installing base dependencies..."
    apt-get install -y \
        curl wget git unzip zip tar \
        build-essential software-properties-common \
        python3 python3-venv python3-pip python3-dev \
        libpq-dev gcc \
        certbot \
        ufw fail2ban \
        cron logrotate \
        >> "$LOG_FILE" 2>&1
    log_info "Base dependencies installed"
}

# ── Install Dependencies (RHEL/AlmaLinux) ───────────────────────────────────

install_deps_dnf() {
    log_step "Updating system packages..."
    dnf update -y >> "$LOG_FILE" 2>&1

    log_step "Installing base dependencies..."
    dnf install -y \
        curl wget git unzip zip tar \
        gcc gcc-c++ make \
        python3 python3-devel python3-pip python3-virtualenv \
        libpq-devel \
        certbot \
        firewalld fail2ban \
        cronie logrotate \
        >> "$LOG_FILE" 2>&1
    log_info "Base dependencies installed"
}

# ── Install Node.js ──────────────────────────────────────────────────────────

install_nodejs() {
    log_step "Installing Node.js 20 LTS..."
    if command -v node &>/dev/null; then
        NODE_VER=$(node --version)
        log_info "Node.js already installed: $NODE_VER"
        return
    fi

    if [ "$PKG_MANAGER" = "apt" ]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >> "$LOG_FILE" 2>&1
        apt-get install -y nodejs >> "$LOG_FILE" 2>&1
    else
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - >> "$LOG_FILE" 2>&1
        dnf install -y nodejs >> "$LOG_FILE" 2>&1
    fi
    log_info "Node.js $(node --version) installed"
}

# ── Install PostgreSQL ───────────────────────────────────────────────────────

install_postgresql() {
    log_step "Installing PostgreSQL..."
    if command -v psql &>/dev/null; then
        log_info "PostgreSQL already installed"
        return
    fi

    if [ "$PKG_MANAGER" = "apt" ]; then
        apt-get install -y postgresql postgresql-contrib >> "$LOG_FILE" 2>&1
    else
        dnf install -y postgresql-server postgresql-contrib >> "$LOG_FILE" 2>&1
        postgresql-setup --initdb >> "$LOG_FILE" 2>&1
    fi

    systemctl enable postgresql >> "$LOG_FILE" 2>&1
    systemctl start postgresql >> "$LOG_FILE" 2>&1

    # Create database and user
    sudo -u postgres psql -c "CREATE USER hostingsignal WITH PASSWORD 'hs_$(openssl rand -hex 8)';" >> "$LOG_FILE" 2>&1 || true
    sudo -u postgres psql -c "CREATE DATABASE hostingsignal OWNER hostingsignal;" >> "$LOG_FILE" 2>&1 || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hostingsignal TO hostingsignal;" >> "$LOG_FILE" 2>&1 || true

    log_info "PostgreSQL installed and configured"
}

# ── Install Redis ────────────────────────────────────────────────────────────

install_redis() {
    log_step "Installing Redis..."
    if command -v redis-server &>/dev/null; then
        log_info "Redis already installed"
        return
    fi

    if [ "$PKG_MANAGER" = "apt" ]; then
        apt-get install -y redis-server >> "$LOG_FILE" 2>&1
    else
        dnf install -y redis >> "$LOG_FILE" 2>&1
    fi

    systemctl enable redis-server >> "$LOG_FILE" 2>&1 || systemctl enable redis >> "$LOG_FILE" 2>&1
    systemctl start redis-server >> "$LOG_FILE" 2>&1 || systemctl start redis >> "$LOG_FILE" 2>&1
    log_info "Redis installed"
}

# ── Install OpenLiteSpeed ────────────────────────────────────────────────────

install_openlitespeed() {
    log_step "Installing OpenLiteSpeed..."
    if [ -d "/usr/local/lsws" ]; then
        log_info "OpenLiteSpeed already installed"
        return
    fi

    if [ "$PKG_MANAGER" = "apt" ]; then
        wget -qO - https://repo.litespeed.sh | bash >> "$LOG_FILE" 2>&1
        apt-get install -y openlitespeed lsphp82 lsphp82-common lsphp82-mysql lsphp82-curl \
            lsphp82-json lsphp82-opcache lsphp82-imap >> "$LOG_FILE" 2>&1
    else
        rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.3-1.el9.noarch.rpm >> "$LOG_FILE" 2>&1 || true
        dnf install -y openlitespeed lsphp82 lsphp82-common lsphp82-mysqlnd >> "$LOG_FILE" 2>&1
    fi

    systemctl enable lsws >> "$LOG_FILE" 2>&1
    systemctl start lsws >> "$LOG_FILE" 2>&1
    log_info "OpenLiteSpeed installed"
}

# ── Install Apache ──────────────────────────────────────────────────────────

install_apache() {
    log_step "Installing Apache with PHP-FPM..."

    if [ "$PKG_MANAGER" = "apt" ]; then
        add-apt-repository -y ppa:ondrej/php >> "$LOG_FILE" 2>&1 || true
        apt-get update -y >> "$LOG_FILE" 2>&1
        apt-get install -y apache2 libapache2-mod-fcgid \
            php8.2 php8.2-fpm php8.2-cli php8.2-common php8.2-mysql \
            php8.2-curl php8.2-gd php8.2-mbstring php8.2-xml \
            php8.2-zip php8.2-intl php8.2-opcache php8.2-redis \
            >> "$LOG_FILE" 2>&1

        a2enmod proxy_fcgi setenvif rewrite ssl headers >> "$LOG_FILE" 2>&1
        a2enconf php8.2-fpm >> "$LOG_FILE" 2>&1 || true

        systemctl enable apache2 >> "$LOG_FILE" 2>&1
        systemctl start apache2 >> "$LOG_FILE" 2>&1
        systemctl enable php8.2-fpm >> "$LOG_FILE" 2>&1
        systemctl start php8.2-fpm >> "$LOG_FILE" 2>&1

    else
        dnf install -y httpd mod_ssl \
            php php-fpm php-cli php-common php-mysqlnd \
            php-curl php-gd php-mbstring php-xml \
            php-zip php-intl php-opcache php-redis \
            >> "$LOG_FILE" 2>&1

        systemctl enable httpd >> "$LOG_FILE" 2>&1
        systemctl start httpd >> "$LOG_FILE" 2>&1
        systemctl enable php-fpm >> "$LOG_FILE" 2>&1
        systemctl start php-fpm >> "$LOG_FILE" 2>&1
    fi

    log_info "Apache with PHP-FPM installed"
}

# ── Web Server Selection ────────────────────────────────────────────────────

select_webserver() {
    # Allow override via environment variable (from compiled installer)
    if [ -n "${HS_WEB_SERVER:-}" ]; then
        WEB_SERVER="$HS_WEB_SERVER"
        log_step "Web server pre-selected: $WEB_SERVER"
        return
    fi

    echo ""
    echo -e "${CYAN}┌─────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│  Select Web Server Engine:           │${NC}"
    echo -e "${CYAN}│                                      │${NC}"
    echo -e "${CYAN}│  1) OpenLiteSpeed (recommended)      │${NC}"
    echo -e "${CYAN}│  2) Apache                           │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────┘${NC}"
    echo ""
    read -p "  Enter choice [1/2] (default: 1): " WEB_CHOICE
    echo ""

    case "$WEB_CHOICE" in
        2)
            WEB_SERVER="apache"
            log_info "Selected: Apache with PHP-FPM"
            ;;
        *)
            WEB_SERVER="openlitespeed"
            log_info "Selected: OpenLiteSpeed (recommended)"
            ;;
    esac
}

# ── Clone & Setup Panel ─────────────────────────────────────────────────────

setup_panel() {
    log_step "Setting up HostingSignal Panel..."

    # Clean previous install
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "Removing previous installation..."
        rm -rf "$INSTALL_DIR"
    fi

    # Clone repository
    git clone "$REPO_URL" "$INSTALL_DIR" >> "$LOG_FILE" 2>&1
    cd "$INSTALL_DIR"

    # Create directories
    mkdir -p "$CONFIG_DIR" "$LOG_DIR" /var/log/hostingsignal/tmp
    mkdir -p /home /var/backups/hostingsignal

    # Generate credentials
    ADMIN_PASS=$(openssl rand -base64 12 | tr -d '/+=')
    DB_PASS=$(openssl rand -hex 12)

    # Backend setup
    log_step "Setting up Python backend..."
    cd "$INSTALL_DIR/backend"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip >> "$LOG_FILE" 2>&1
    pip install -r requirements.txt >> "$LOG_FILE" 2>&1

    cat > .env << EOF
APP_NAME=HostingSignal
APP_VERSION=${PANEL_VERSION}
DEBUG=False
ADMIN_PASSWORD=${ADMIN_PASS}
DATABASE_URL=sqlite+aiosqlite:///./hostingsignal.db
REDIS_URL=redis://localhost:6379/0
EOF

    deactivate

    # Frontend setup
    log_step "Building Next.js frontend..."
    cd "$INSTALL_DIR/frontend"
    npm install >> "$LOG_FILE" 2>&1
    npm run build >> "$LOG_FILE" 2>&1

    # Install CLI tool
    log_step "Installing hsctl CLI..."
    cd "$INSTALL_DIR/cli"
    pip3 install -e . >> "$LOG_FILE" 2>&1

    log_info "Panel setup complete"
}

# ── Configure Services ──────────────────────────────────────────────────────

configure_services() {
    log_step "Configuring systemd services..."

    # Install service files
    cp "$INSTALL_DIR/systemd/hostingsignal-api.service" /etc/systemd/system/
    cp "$INSTALL_DIR/systemd/hostingsignal-web.service" /etc/systemd/system/
    cp "$INSTALL_DIR/systemd/hostingsignal-daemon.service" /etc/systemd/system/
    cp "$INSTALL_DIR/systemd/hostingsignal-monitor.service" /etc/systemd/system/

    systemctl daemon-reload

    # Enable and start services
    systemctl enable hostingsignal-api hostingsignal-web hostingsignal-daemon hostingsignal-monitor >> "$LOG_FILE" 2>&1
    systemctl start hostingsignal-api >> "$LOG_FILE" 2>&1
    systemctl start hostingsignal-web >> "$LOG_FILE" 2>&1
    systemctl start hostingsignal-daemon >> "$LOG_FILE" 2>&1 || true
    systemctl start hostingsignal-monitor >> "$LOG_FILE" 2>&1 || true

    log_info "Services configured and started"
}

# ── Configure Firewall ──────────────────────────────────────────────────────

configure_firewall() {
    log_step "Configuring firewall..."

    if command -v ufw &>/dev/null; then
        ufw allow 22/tcp >> "$LOG_FILE" 2>&1 || true
        ufw allow 80/tcp >> "$LOG_FILE" 2>&1 || true
        ufw allow 443/tcp >> "$LOG_FILE" 2>&1 || true
        ufw allow 3000/tcp >> "$LOG_FILE" 2>&1 || true
        ufw allow 8000/tcp >> "$LOG_FILE" 2>&1 || true
        ufw allow 7080/tcp >> "$LOG_FILE" 2>&1 || true
        echo "y" | ufw enable >> "$LOG_FILE" 2>&1 || true
    elif command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-service=ssh >> "$LOG_FILE" 2>&1 || true
        firewall-cmd --permanent --add-service=http >> "$LOG_FILE" 2>&1 || true
        firewall-cmd --permanent --add-service=https >> "$LOG_FILE" 2>&1 || true
        firewall-cmd --permanent --add-port=3000/tcp >> "$LOG_FILE" 2>&1 || true
        firewall-cmd --permanent --add-port=8000/tcp >> "$LOG_FILE" 2>&1 || true
        firewall-cmd --permanent --add-port=7080/tcp >> "$LOG_FILE" 2>&1 || true
        firewall-cmd --reload >> "$LOG_FILE" 2>&1 || true
    fi

    log_info "Firewall configured"
}

# ── Configure Fail2Ban ──────────────────────────────────────────────────────

configure_fail2ban() {
    log_step "Configuring Fail2Ban..."
    
    cat > /etc/fail2ban/jail.d/hostingsignal.conf << 'EOF'
[hostingsignal]
enabled = true
port = 3000,8000
filter = hostingsignal
logpath = /var/log/hostingsignal/*.log
maxretry = 5
bantime = 600
findtime = 600
EOF

    cat > /etc/fail2ban/filter.d/hostingsignal.conf << 'EOF'
[Definition]
failregex = ^.*Failed login attempt from <HOST>.*$
            ^.*Authentication failed for .* from <HOST>.*$
ignoreregex =
EOF

    systemctl enable fail2ban >> "$LOG_FILE" 2>&1
    systemctl restart fail2ban >> "$LOG_FILE" 2>&1 || true

    log_info "Fail2Ban configured"
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
    banner
    preflight

    # Install dependencies based on OS
    if [ "$PKG_MANAGER" = "apt" ]; then
        install_deps_apt
    else
        install_deps_dnf
    fi

    install_nodejs
    install_postgresql
    install_redis

    # Web server selection
    select_webserver
    if [ "$WEB_SERVER" = "apache" ]; then
        install_apache
    else
        install_openlitespeed
    fi

    setup_panel
    configure_services
    configure_firewall
    configure_fail2ban

    # Get server IP
    SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')

    # Final output
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}[✓] HostingSignal Panel Installation Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Panel URL:${NC}       http://${SERVER_IP}:3000"
    echo -e "  ${BOLD}API URL:${NC}         http://${SERVER_IP}:8000"
    echo -e "  ${BOLD}API Docs:${NC}        http://${SERVER_IP}:8000/api/docs"
    echo -e "  ${BOLD}OLS Admin:${NC}       https://${SERVER_IP}:7080"
    echo ""
    echo -e "  ${YELLOW}Admin Credentials:${NC}"
    echo -e "  ${BOLD}Email:${NC}           admin@hostingsignal.com"
    echo -e "  ${BOLD}Password:${NC}        ${ADMIN_PASS}"
    echo ""
    echo -e "  ${CYAN}CLI Tool:${NC}        hsctl status"
    echo -e "  ${CYAN}Installation Log:${NC} ${LOG_FILE}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

main "$@"
