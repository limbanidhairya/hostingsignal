#!/bin/bash
###############################################################################
# HostingSignal — Universal Installer
# Supports: Ubuntu 22.04+, AlmaLinux 8+, CentOS 8+, Rocky 8+
#
# Usage:
#   sh <(curl -fsSL https://install.hostingsignal.com)
###############################################################################

set -e

# ── Branding ────────────────────────────────────────────────────────────
PANEL_NAME="HostingSignal"
PANEL_VERSION="1.0.0"
INSTALL_DIR="/opt/hostingsignal"
PANEL_PORT=8090
BACKEND_PORT=8000

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   ██╗  ██╗ ██████╗ ███████╗████████╗██╗███╗   ██╗ ██████╗    ║"
    echo "║   ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝██║████╗  ██║██╔════╝    ║"
    echo "║   ███████║██║   ██║███████╗   ██║   ██║██╔██╗ ██║██║  ███╗   ║"
    echo "║   ██╔══██║██║   ██║╚════██║   ██║   ██║██║╚██╗██║██║   ██║   ║"
    echo "║   ██║  ██║╚██████╔╝███████║   ██║   ██║██║ ╚████║╚██████╔╝   ║"
    echo "║   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝    ║"
    echo "║                    ███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗     ║"
    echo "║                    ██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║     ║"
    echo "║                    ███████╗██║██║  ███╗██╔██╗ ██║███████║██║     ║"
    echo "║                    ╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║     ║"
    echo "║                    ███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗║"
    echo "║                    ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝║"
    echo "║                                                               ║"
    echo "║              Web Hosting Control Panel v${PANEL_VERSION}              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "${BLUE}[→]${NC} $1"; }


# ── Pre-flight checks ──────────────────────────────────────────────────
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This installer must be run as root."
        echo "  Run: sudo bash install.sh"
        exit 1
    fi
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        log_error "Cannot detect operating system."
        exit 1
    fi
    . /etc/os-release
    OS_NAME="$ID"
    OS_VERSION="$VERSION_ID"
    OS_MAJOR="${OS_VERSION%%.*}"

    case "$OS_NAME" in
        ubuntu)
            if [ "$OS_MAJOR" -lt 22 ]; then
                log_error "Ubuntu $OS_VERSION is not supported. Minimum: 22.04"
                exit 1
            fi
            OS_FAMILY="debian"
            ;;
        almalinux|rocky)
            if [ "$OS_MAJOR" -lt 8 ]; then
                log_error "$PRETTY_NAME is not supported. Minimum: 8.x"
                exit 1
            fi
            OS_FAMILY="rhel"
            ;;
        centos)
            if [ "$OS_MAJOR" -lt 8 ]; then
                log_error "CentOS $OS_VERSION is not supported. Minimum: 8 Stream"
                exit 1
            fi
            OS_FAMILY="rhel"
            ;;
        *)
            log_error "Unsupported operating system: $PRETTY_NAME"
            echo "  Supported: Ubuntu 22.04+, AlmaLinux 8+, CentOS 8+, Rocky 8+"
            exit 1
            ;;
    esac
    log_info "Detected: $PRETTY_NAME ($OS_FAMILY family)"
}

check_memory() {
    TOTAL_MEM=$(free -m | awk '/Mem:/ {print $2}')
    if [ "$TOTAL_MEM" -lt 1024 ]; then
        log_warn "Low memory detected: ${TOTAL_MEM}MB (1GB+ recommended)"
    else
        log_info "Memory: ${TOTAL_MEM}MB ✓"
    fi
}

check_disk() {
    FREE_DISK=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "$FREE_DISK" -lt 10 ]; then
        log_error "Insufficient disk space: ${FREE_DISK}GB (10GB+ required)"
        exit 1
    fi
    log_info "Disk space: ${FREE_DISK}GB free ✓"
}


# ── Install services ───────────────────────────────────────────────────
install_dependencies() {
    log_step "Installing system dependencies..."
    if [ "$OS_FAMILY" = "debian" ]; then
        source "$(dirname "$0")/setup_ubuntu.sh" 2>/dev/null || bash <(curl -fsSL https://raw.githubusercontent.com/hostingsignal/installer/main/setup_ubuntu.sh)
    else
        source "$(dirname "$0")/setup_rhel.sh" 2>/dev/null || bash <(curl -fsSL https://raw.githubusercontent.com/hostingsignal/installer/main/setup_rhel.sh)
    fi
}


# ── Install HostingSignal ──────────────────────────────────────────────
install_panel() {
    log_step "Installing ${PANEL_NAME}..."

    # Clone repo
    mkdir -p "$INSTALL_DIR"
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR" && git pull
    else
        git clone https://github.com/hostingsignal/hostingsignal.git "$INSTALL_DIR"
    fi

    # Backend setup
    log_step "Setting up backend..."
    cd "$INSTALL_DIR/backend"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # Generate secrets
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    cat > .env <<EOF
DATABASE_URL=sqlite+aiosqlite:///./hostingsignal.db
SECRET_KEY=${SECRET_KEY}
APP_NAME=${PANEL_NAME}
CORS_ORIGINS=["https://$(hostname -f):${PANEL_PORT}", "https://$(curl -4 -s ifconfig.me):${PANEL_PORT}"]
HS_DEV_MODE=0
EOF
    log_info "Backend configured"

    # Frontend setup
    log_step "Building frontend..."
    cd "$INSTALL_DIR/frontend"
    npm install
    cat > .env.local <<EOF
NEXT_PUBLIC_API_URL=https://$(hostname -f):${BACKEND_PORT}
EOF
    npm run build
    log_info "Frontend built"
}


# ── Configure systemd services ─────────────────────────────────────────
setup_systemd() {
    log_step "Creating systemd services..."

    # Backend service
    cat > /etc/systemd/system/hostingsignal-api.service <<EOF
[Unit]
Description=${PANEL_NAME} API Server
After=network.target mariadb.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/backend
Environment=PATH=${INSTALL_DIR}/backend/venv/bin:/usr/local/bin:/usr/bin
ExecStart=${INSTALL_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Frontend service
    cat > /etc/systemd/system/hostingsignal-web.service <<EOF
[Unit]
Description=${PANEL_NAME} Web Interface
After=network.target hostingsignal-api.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/npx next start -p ${PANEL_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable hostingsignal-api hostingsignal-web
    systemctl start hostingsignal-api hostingsignal-web
    log_info "Services created and started"
}


# ── Lock installation directories ──────────────────────────────────────
lock_directories() {
    log_step "Locking panel installation directories..."
    # Set panel files to root-only, read-only
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    # Make key config files immutable
    chattr +i "$INSTALL_DIR/backend/.env" 2>/dev/null || true
    chattr +i "$INSTALL_DIR/frontend/.env.local" 2>/dev/null || true
    log_info "Panel directories locked (read-only, root-owned)"
}


# ── Configure firewall ─────────────────────────────────────────────────
setup_firewall() {
    log_step "Configuring firewall..."
    if command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        firewall-cmd --permanent --add-port=${PANEL_PORT}/tcp
        firewall-cmd --permanent --add-port=${BACKEND_PORT}/tcp
        firewall-cmd --permanent --add-port=22/tcp
        firewall-cmd --permanent --add-port=25/tcp
        firewall-cmd --permanent --add-port=587/tcp
        firewall-cmd --permanent --add-port=993/tcp
        firewall-cmd --permanent --add-port=53/tcp
        firewall-cmd --permanent --add-port=53/udp
        firewall-cmd --reload
    elif command -v ufw &>/dev/null; then
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow ${PANEL_PORT}/tcp
        ufw allow ${BACKEND_PORT}/tcp
        ufw allow 22/tcp
        ufw allow 25/tcp
        ufw allow 587/tcp
        ufw allow 993/tcp
        ufw allow 53/tcp
        ufw allow 53/udp
        ufw --force enable
    fi
    log_info "Firewall configured"
}


# ── Print completion info ──────────────────────────────────────────────
print_complete() {
    SERVER_IP=$(curl -4 -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            ✅ ${PANEL_NAME} Installed Successfully!            ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🌐 Panel URL:    ${CYAN}https://${SERVER_IP}:${PANEL_PORT}${NC}"
    echo -e "${GREEN}║${NC}  📡 API URL:      ${CYAN}https://${SERVER_IP}:${BACKEND_PORT}${NC}"
    echo -e "${GREEN}║${NC}  📄 API Docs:     ${CYAN}https://${SERVER_IP}:${BACKEND_PORT}/api/docs${NC}"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  👤 Default Login:"
    echo -e "${GREEN}║${NC}     Email:    ${YELLOW}admin@hostingsignal.com${NC}"
    echo -e "${GREEN}║${NC}     Password: ${YELLOW}admin123${NC}"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${RED}⚠  Change the admin password immediately after login!${NC}"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Complete the setup wizard at the URL above."
    echo -e "${GREEN}║${NC}  You will be guided through:"
    echo -e "${GREEN}║${NC}     1. Terms & Conditions"
    echo -e "${GREEN}║${NC}     2. Account configuration"
    echo -e "${GREEN}║${NC}     3. License activation"
    echo -e "${GREEN}║${NC}     4. Server settings"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}


# ── Main ───────────────────────────────────────────────────────────────
main() {
    banner
    check_root
    check_os
    check_memory
    check_disk
    echo ""
    log_step "Starting ${PANEL_NAME} v${PANEL_VERSION} installation..."
    echo ""
    install_dependencies
    install_panel
    setup_systemd
    lock_directories
    setup_firewall
    print_complete
}

main "$@"
