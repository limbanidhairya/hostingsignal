#!/bin/bash
###############################################################################
# HostingSignal Panel — Update Script
# Called by: hsctl update
# Downloads from: https://updates.hostingsignal.in
###############################################################################
set -euo pipefail

INSTALL_DIR="/usr/local/hostingsignal"
UPDATE_URL="https://updates.hostingsignal.in/latest/stable"
LOG_FILE="/var/log/hostingsignal/update.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "HostingSignal Update started"

# Check current version
CURRENT_VERSION=$(cat "$INSTALL_DIR/VERSION" 2>/dev/null || echo "unknown")
log "Current version: $CURRENT_VERSION"

# Check for updates
log "Checking for updates..."
LATEST_VERSION=$(curl -sSL "$UPDATE_URL/version.txt" 2>/dev/null || echo "unknown")
log "Latest version: $LATEST_VERSION"

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    log "Already up to date."
    exit 0
fi

# Create backup
log "Creating pre-update backup..."
tar -czf "/var/backups/hostingsignal/pre-update-${TIMESTAMP}.tar.gz" \
    -C "$INSTALL_DIR" \
    --exclude='node_modules' --exclude='venv' --exclude='.git' \
    . 2>/dev/null || true

# Download update
log "Downloading update package..."
curl -sSL -o /tmp/hs-update.tar.gz "$UPDATE_URL/hostingsignal-${LATEST_VERSION}.tar.gz"

# Stop services
log "Stopping services..."
systemctl stop hostingsignal-web hostingsignal-api hostingsignal-daemon hostingsignal-monitor 2>/dev/null || true

# Extract update (preserve config)
log "Installing update..."
tar -xzf /tmp/hs-update.tar.gz -C "$INSTALL_DIR" --exclude='config/*' --exclude='.env'

# Update backend dependencies
log "Updating backend dependencies..."
cd "$INSTALL_DIR/backend"
source venv/bin/activate
pip install -r requirements.txt >> "$LOG_FILE" 2>&1
deactivate

# Rebuild frontend
log "Rebuilding frontend..."
cd "$INSTALL_DIR/frontend"
npm install >> "$LOG_FILE" 2>&1
npm run build >> "$LOG_FILE" 2>&1

# Update service files
log "Updating service files..."
cp "$INSTALL_DIR/systemd/"*.service /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload

# Update version file
echo "$LATEST_VERSION" > "$INSTALL_DIR/VERSION"

# Start services
log "Starting services..."
systemctl start hostingsignal-api hostingsignal-web hostingsignal-daemon hostingsignal-monitor

# Cleanup
rm -f /tmp/hs-update.tar.gz

log "Update complete: $CURRENT_VERSION → $LATEST_VERSION"
