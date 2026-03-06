#!/bin/bash
###############################################################################
# HostingSignal - Master Installation Script
# https://github.com/limbanidhairya/hostingsignal
###############################################################################
set -e

# --- UI Helpers ---
log_info()  { echo -e "\033[0;32m[✓]\033[0m $1"; }
log_step()  { echo -e "\033[0;36m[→]\033[0m $1"; }
log_warn()  { echo -e "\033[0;33m[!]\033[0m $1"; }
log_err()   { echo -e "\033[0;31m[x]\033[0m $1"; exit 1; }

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

# Ensure run as root
if [ "$(id -u)" != "0" ]; then
    log_err "This script must be run as root. (e.g., sudo bash install.sh)"
fi

# 1. System Updates
log_step "Updating OS packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get upgrade -y

# 2. Clone Git Repo
INSTALL_DIR="/usr/local/hostingsignal"
log_step "Cloning HostingSignal from GitHub to $INSTALL_DIR..."
apt-get install -y git
if [ -d "$INSTALL_DIR" ]; then
    log_warn "Directory $INSTALL_DIR already exists. Purging old files to ensure a clean install..."
    rm -rf "$INSTALL_DIR"
fi
git clone https://github.com/limbanidhairya/hostingsignal.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 3. Run Underlying Dependency Installer
if [ -f "$INSTALL_DIR/installer/setup_ubuntu.sh" ]; then
    log_step "Running system dependencies installer (OpenLiteSpeed, MariaDB, etc.)..."
    chmod +x "$INSTALL_DIR/installer/setup_ubuntu.sh"
    bash "$INSTALL_DIR/installer/setup_ubuntu.sh"
else
    log_err "Required script installer/setup_ubuntu.sh not found!"
fi

# 4. Generate Secure Admin Credentials
log_step "Generating secure Admin credentials..."
ADMIN_PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16)
cat <<EOL > "$INSTALL_DIR/backend/.env"
APP_NAME="HostingSignal"
APP_VERSION="1.0.0"
DEBUG=False
ADMIN_PASSWORD="$ADMIN_PASS"
EOL
log_info "Generated backend environment and admin password."

# 5. Setup Python Backend
log_step "Setting up Python Backend environment..."
cd "$INSTALL_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    log_warn "backend/requirements.txt missing, installing minimum dependencies..."
    pip install fastapi uvicorn sqlalchemy aiosqlite pydantic_settings passlib[bcrypt] python-jose[cryptography] python-multipart
fi
deactivate

# 6. Build Next.js Frontend
log_step "Building Frontend (Next.js)..."
cd "$INSTALL_DIR/frontend"
# Install dependencies if node_modules is missing
if [ ! -d "node_modules" ]; then
    npm install
fi
# Build application (generates .next)
npm run build
log_info "Frontend build complete."

# 7. Create SystemD Services
log_step "Configuring Systemd daemon services..."

# Backend Service
cat <<EOL > /etc/systemd/system/hostingsignal-backend.service
[Unit]
Description=HostingSignal FastAPI Backend
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/backend/venv/bin"
ExecStart=$INSTALL_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Frontend Service
cat <<EOL > /etc/systemd/system/hostingsignal-frontend.service
[Unit]
Description=HostingSignal Next.js Frontend
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR/frontend
ExecStart=/usr/bin/npm start
Restart=always
Environment="PORT=3000"

[Install]
WantedBy=multi-user.target
EOL

# Reload, Enable, and Start Services
systemctl daemon-reload
systemctl enable hostingsignal-backend hostingsignal-frontend
systemctl restart hostingsignal-backend hostingsignal-frontend

# Get Server IP
SERVER_IP=$(curl -s http://checkip.amazonaws.com || echo "YOUR_SERVER_IP")

echo ""
echo "================================================================="
log_info "HostingSignal Installation Completed Successfully!"
echo "================================================================="
echo "You can now access your control panel at:"
echo -e "\033[1;36mURL: \033[0m http://$SERVER_IP:3000"
echo ""
echo -e "\033[1;33mAdmin Login Credentials:\033[0m"
echo -e "Username: \033[1;32madmin@hostingsignal.com\033[0m"
echo -e "Password: \033[1;32m$ADMIN_PASS\033[0m"
echo ""
echo "Note: If you have a firewall running, ensure ports 3000 and 8000 are open."
echo "Keep these credentials safe. Welcome to HostingSignal!"
echo "================================================================="
echo ""
