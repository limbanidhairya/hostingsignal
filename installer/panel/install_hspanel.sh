#!/usr/bin/env bash
# HS-Panel Installer — Panel Installation
# Clones the repository and installs both the API backend and Next.js frontend.

HSPANEL_INSTALL_DIR="${HSPANEL_INSTALL_DIR:-/usr/local/hspanel}"
HSPANEL_REPO="${HSPANEL_REPO:-https://github.com/limbanidhairya/hostingsignal}"
HSPANEL_BRANCH="${HSPANEL_BRANCH:-main}"
HSPANEL_ADMIN_USER="${HSPANEL_ADMIN_USER:-admin}"
HSPANEL_ADMIN_PASSWD="${HSPANEL_ADMIN_PASSWD:-}"

install_hspanel() {
  log_info "Installing HS-Panel from $HSPANEL_REPO..."

  [[ -z "$HSPANEL_ADMIN_PASSWD" ]] && \
    HSPANEL_ADMIN_PASSWD="$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 18)"

  # Clone or update
  if [[ -d "$HSPANEL_INSTALL_DIR/.git" ]]; then
    log_info "Repository already present — pulling latest..."
    git -C "$HSPANEL_INSTALL_DIR" pull --quiet origin "$HSPANEL_BRANCH" || \
      log_warning "git pull failed — using existing files"
  else
    git clone --depth 1 --branch "$HSPANEL_BRANCH" "$HSPANEL_REPO" "$HSPANEL_INSTALL_DIR"
  fi

  rollback_remove_dir "$HSPANEL_INSTALL_DIR"

  # Create runtime directories
  mkdir -p \
    "$HSPANEL_INSTALL_DIR/logs" \
    "$HSPANEL_INSTALL_DIR/configs" \
    "/var/hspanel/queue/done" \
    "/var/hspanel/userdata" \
    "/var/hspanel/users" \
    "/var/log/hspanel"

  _install_panel_api
  _install_panel_web
  _install_panel_services
  _install_panel_systemd_units

  log_success "HS-Panel cloned and services installed"
  mark_service_done "hspanel"
}

_install_panel_api() {
  local api_dir="${HSPANEL_INSTALL_DIR}/developer-panel/api"
  [[ -d "$api_dir" ]] || { log_warning "API directory not found — skipping Python deps"; return 0; }

  log_info "  Setting up Python virtual environment for API..."
  python3 -m venv "${HSPANEL_INSTALL_DIR}/.venv"
  "${HSPANEL_INSTALL_DIR}/.venv/bin/pip" install --quiet --upgrade pip

  local req="${HSPANEL_INSTALL_DIR}/developer-panel/requirements.txt"
  [[ -f "$req" ]] && "${HSPANEL_INSTALL_DIR}/.venv/bin/pip" install --quiet -r "$req"

  log_success "  API Python environment ready"
}

_install_panel_web() {
  local web_dir="${HSPANEL_INSTALL_DIR}/developer-panel/web"
  [[ -d "$web_dir" ]] || { log_warning "Web directory not found — skipping Node build"; return 0; }

  if ! command -v node &>/dev/null; then
    log_warning "  Node.js not found — installing..."
    install_nodejs 20
  fi

  log_info "  Installing Node.js dependencies and building web panel..."
  npm --prefix "$web_dir" ci --silent
  npm --prefix "$web_dir" run build

  log_success "  Web panel built"
}

_install_panel_services() {
  local svc_dir="${HSPANEL_INSTALL_DIR}/developer-panel/services"
  [[ -d "$svc_dir" ]] || return 0

  local req="${svc_dir}/requirements.txt"
  if [[ -f "$req" ]]; then
    "${HSPANEL_INSTALL_DIR}/.venv/bin/pip" install --quiet -r "$req" 2>/dev/null || true
  fi
}

_install_panel_systemd_units() {
  local unit_src="${HSPANEL_INSTALL_DIR}/systemd"
  [[ -d "$unit_src" ]] || return 0

  log_info "  Installing systemd service units..."

  # API service
  cat > /etc/systemd/system/hostingsignal-api.service <<SVC
[Unit]
Description=HostingSignal Developer Panel API
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=root
WorkingDirectory=${HSPANEL_INSTALL_DIR}
ExecStart=${HSPANEL_INSTALL_DIR}/.venv/bin/uvicorn developer-panel.api.main:app --host 0.0.0.0 --port 2087 --workers 2
Restart=always
RestartSec=5
Environment=PYTHONPATH=${HSPANEL_INSTALL_DIR}
EnvironmentFile=-/etc/hostingsignal/hostingsignal-devapi.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

  # Web service
  cat > /etc/systemd/system/hostingsignal-web.service <<SVC
[Unit]
Description=HostingSignal Web Panel (Next.js)
After=network.target hostingsignal-api.service

[Service]
Type=simple
User=root
WorkingDirectory=${HSPANEL_INSTALL_DIR}/developer-panel/web
ExecStart=/usr/bin/node .next/standalone/server.js
Restart=always
RestartSec=5
Environment=PORT=3000
Environment=NODE_ENV=production
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

  # Daemon service
  cat > /etc/systemd/system/hostingsignal-daemon.service <<SVC
[Unit]
Description=HostingSignal Task Daemon
After=network.target mariadb.service

[Service]
Type=simple
User=root
WorkingDirectory=${HSPANEL_INSTALL_DIR}/usr/local/hspanel/daemon
ExecStart=/usr/bin/perl hs-taskd.pl
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

  systemctl daemon-reload

  systemctl enable --now hostingsignal-api  2>/dev/null || log_warning "  hostingsignal-api could not start (check config)"
  systemctl enable --now hostingsignal-web  2>/dev/null || log_warning "  hostingsignal-web could not start (check config)"

  log_success "  Systemd units installed"
}
