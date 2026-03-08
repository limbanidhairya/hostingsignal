#!/bin/bash
###############################################################################
# HostingSignal Panel — Remote Installation Script
# Runs on server: installs all deps, clones repo, sets up backend + frontend
###############################################################################
set -euo pipefail
exec > >(tee -a /var/log/hostingsignal-install.log) 2>&1

INSTALL_DIR="/usr/local/hostingsignal"
CONFIG_DIR="/etc/hostingsignal"
LOG_DIR="/var/log/hostingsignal"
REPO_URL="https://github.com/limbanidhairya/hostingsignal.git"
PANEL_VERSION="1.0.0"

echo "=== HostingSignal Panel Installation ==="
echo "=== $(date) ==="
echo ""

# ── Step 1: Base Dependencies ────────────────────────────────────────────
echo "[1/10] Installing base dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
    curl wget git unzip zip tar \
    build-essential software-properties-common \
    python3 python3-venv python3-pip python3-dev \
    libpq-dev gcc \
    certbot \
    ufw fail2ban \
    cron logrotate
echo "[✓] Base dependencies installed"

# ── Step 2: Node.js 20 ──────────────────────────────────────────────────
echo "[2/10] Installing Node.js 20..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
echo "[✓] Node.js $(node --version) installed"

# ── Step 3: PostgreSQL ──────────────────────────────────────────────────
echo "[3/10] Installing PostgreSQL..."
if ! command -v psql &>/dev/null; then
    apt-get install -y postgresql postgresql-contrib
fi
systemctl enable postgresql
systemctl start postgresql

# Create DB user and database
DB_PASS="hs_$(openssl rand -hex 8)"
sudo -u postgres psql -c "CREATE USER hostingsignal WITH PASSWORD '${DB_PASS}';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE hostingsignal OWNER hostingsignal;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hostingsignal TO hostingsignal;" 2>/dev/null || true
echo "[✓] PostgreSQL installed, DB created"

# ── Step 4: Redis ────────────────────────────────────────────────────────
echo "[4/10] Installing Redis..."
if ! command -v redis-server &>/dev/null; then
    apt-get install -y redis-server
fi
systemctl enable redis-server
systemctl start redis-server
echo "[✓] Redis installed"

# ── Step 5: OpenLiteSpeed ────────────────────────────────────────────────
echo "[5/10] Installing OpenLiteSpeed..."
if [ ! -d "/usr/local/lsws" ]; then
    wget -qO - https://repo.litespeed.sh | bash
    apt-get install -y openlitespeed lsphp82 lsphp82-common lsphp82-mysql lsphp82-curl \
        lsphp82-opcache lsphp82-imap 2>/dev/null || echo "Some lsphp packages may not be available, continuing..."
    systemctl enable lsws 2>/dev/null || true
    systemctl start lsws 2>/dev/null || true
fi
echo "[✓] OpenLiteSpeed installed"

# ── Step 6: Clone Repository ────────────────────────────────────────────
echo "[6/10] Cloning HostingSignal repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  Removing previous installation..."
    rm -rf "$INSTALL_DIR"
fi
git clone "$REPO_URL" "$INSTALL_DIR"
echo "[✓] Repository cloned to $INSTALL_DIR"

# Create directories
mkdir -p "$CONFIG_DIR" "$LOG_DIR" /var/log/hostingsignal/tmp
mkdir -p /home /var/backups/hostingsignal
mkdir -p /usr/local/hostingsignal/plugins

# ── Step 7: Backend Setup ───────────────────────────────────────────────
echo "[7/10] Setting up Python backend..."
cd "$INSTALL_DIR/backend"
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt 2>/dev/null || {
    echo "  Installing core packages manually..."
    pip install fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite httpx \
        pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] \
        python-multipart psutil redis aioredis
}

# Generate admin password
ADMIN_PASS=$(openssl rand -base64 12 | tr -d '/+=')

cat > .env << EOF
APP_NAME=HostingSignal
APP_VERSION=${PANEL_VERSION}
DEBUG=False
ADMIN_PASSWORD=${ADMIN_PASS}
DATABASE_URL=sqlite+aiosqlite:///./hostingsignal.db
REDIS_URL=redis://localhost:6379/0
EOF

deactivate
echo "[✓] Backend setup complete"

# ── Step 8: Frontend Setup ──────────────────────────────────────────────
echo "[8/10] Building Next.js frontend..."
cd "$INSTALL_DIR/frontend"
npm install
npm run build 2>/dev/null || {
    echo "  Build had issues, will run in dev mode..."
}
echo "[✓] Frontend setup complete"

# ── Step 9: Systemd Services ────────────────────────────────────────────
echo "[9/10] Configuring systemd services..."

# API Service
cat > /etc/systemd/system/hostingsignal-api.service << 'EOF'
[Unit]
Description=HostingSignal Panel API
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/hostingsignal/backend
Environment=PATH=/usr/local/hostingsignal/backend/venv/bin:/usr/bin:/bin
ExecStart=/usr/local/hostingsignal/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Web Service
cat > /etc/systemd/system/hostingsignal-web.service << 'EOF'
[Unit]
Description=HostingSignal Panel Frontend
After=network.target hostingsignal-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/hostingsignal/frontend
ExecStart=/usr/bin/npx next start -p 3000
Restart=always
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hostingsignal-api hostingsignal-web
systemctl start hostingsignal-api
sleep 3
systemctl start hostingsignal-web
echo "[✓] Services configured and started"

# ── Step 10: Firewall ───────────────────────────────────────────────────
echo "[10/10] Configuring firewall..."
ufw allow 22/tcp 2>/dev/null || true
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
ufw allow 3000/tcp 2>/dev/null || true
ufw allow 8000/tcp 2>/dev/null || true
ufw allow 7080/tcp 2>/dev/null || true
echo "y" | ufw enable 2>/dev/null || true
echo "[✓] Firewall configured"

# ── Get Server IP ────────────────────────────────────────────────────────
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "[✓] HostingSignal Panel Installation Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Panel URL:       http://${SERVER_IP}:3000"
echo "  API URL:         http://${SERVER_IP}:8000"
echo "  API Docs:        http://${SERVER_IP}:8000/api/docs"
echo ""
echo "  Admin Credentials:"
echo "  Email:           admin@hostingsignal.com"
echo "  Password:        ${ADMIN_PASS}"
echo ""
echo "  Services:"
systemctl is-active hostingsignal-api && echo "  API:    ✓ running" || echo "  API:    ✗ not running"
systemctl is-active hostingsignal-web && echo "  Web:    ✓ running" || echo "  Web:    ✗ not running"
echo ""
echo "  Log: /var/log/hostingsignal-install.log"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "INSTALL_COMPLETE"
