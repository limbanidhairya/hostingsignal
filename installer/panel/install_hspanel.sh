#!/usr/bin/env bash
# HS-Panel Installer — Native Panel Installation
# Clones repository into /opt/hostingsignal and prepares native services.

HSPANEL_INSTALL_DIR="${HSPANEL_INSTALL_DIR:-/opt/hostingsignal}"
HSPANEL_REPO="${HSPANEL_REPO:-https://github.com/limbanidhairya/hostingsignal}"
HSPANEL_BRANCH="${HSPANEL_BRANCH:-main}"
HSPANEL_ADMIN_USER="${HSPANEL_ADMIN_USER:-admin}"
HSPANEL_ADMIN_PASSWD="${HSPANEL_ADMIN_PASSWD:-}"
HSPANEL_ADMIN_EMAIL="${HSPANEL_ADMIN_EMAIL:-admin@hostingsignal.local}"

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

  # Create production layout
  mkdir -p \
    "$HSPANEL_INSTALL_DIR/logs" \
    "$HSPANEL_INSTALL_DIR/deployment" \
    "$HSPANEL_INSTALL_DIR/services" \
    "$HSPANEL_INSTALL_DIR/scripts" \
    "$HSPANEL_INSTALL_DIR/api" \
    "$HSPANEL_INSTALL_DIR/frontend" \
    "/var/hspanel/queue/done" \
    "/var/hspanel/userdata" \
    "/home/sites" \
    "/home/mail" \
    "/home/users" \
    "/etc/powerdns/zones" \
    "/var/log/hspanel"

  # Stable shortcuts for requested production structure.
  ln -sfn "$HSPANEL_INSTALL_DIR/usr/local/hspanel/backend" "$HSPANEL_INSTALL_DIR/api"
  ln -sfn "$HSPANEL_INSTALL_DIR/developer-panel/web" "$HSPANEL_INSTALL_DIR/frontend"
  ln -sfn "$HSPANEL_INSTALL_DIR/usr/local/hspanel/scripts" "$HSPANEL_INSTALL_DIR/scripts/panel"

  _install_panel_api
  _install_panel_web
  _install_panel_services
  _install_worker_script

  if [[ -d "${HSPANEL_INSTALL_DIR}/usr/local/hspanel/scripts/provision" ]]; then
    chmod +x "${HSPANEL_INSTALL_DIR}"/usr/local/hspanel/scripts/provision/*.sh 2>/dev/null || true
  fi

  log_success "HS-Panel repository prepared"
  mark_service_done "hspanel"
}

_install_panel_api() {
  local api_dir="${HSPANEL_INSTALL_DIR}/usr/local/hspanel/backend/api"
  [[ -d "$api_dir" ]] || { log_warning "Backend API directory not found — skipping Python deps"; return 0; }

  log_info "  Setting up Python virtual environment for API..."
  python3 -m venv "${HSPANEL_INSTALL_DIR}/.venv"
  "${HSPANEL_INSTALL_DIR}/.venv/bin/pip" install --quiet --upgrade pip

  local req
  req="${HSPANEL_INSTALL_DIR}/usr/local/hspanel/backend/requirements.txt"
  [[ -f "$req" ]] && "${HSPANEL_INSTALL_DIR}/.venv/bin/pip" install --quiet -r "$req"

  local dev_req
  dev_req="${HSPANEL_INSTALL_DIR}/developer-panel/requirements.txt"
  [[ -f "$dev_req" ]] && "${HSPANEL_INSTALL_DIR}/.venv/bin/pip" install --quiet -r "$dev_req"

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
  npm --prefix "$web_dir" install --silent
  HSDEV_INTERNAL_API_BASE="http://127.0.0.1:3000" \
  NEXT_PUBLIC_HSDEV_API_BASE="/devapi" \
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

_install_worker_script() {
  local worker_script="${HSPANEL_INSTALL_DIR}/scripts/hspanel_worker.sh"
  cat > "$worker_script" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

QUEUE_DIR="/var/hspanel/queue"
DONE_DIR="/var/hspanel/queue/done"

mkdir -p "$QUEUE_DIR" "$DONE_DIR"

while true; do
  shopt -s nullglob
  jobs=("$QUEUE_DIR"/*.json)
  shopt -u nullglob

  if [[ "${#jobs[@]}" -eq 0 ]]; then
    sleep 2
    continue
  fi

  for job in "${jobs[@]}"; do
    job_name="$(basename "$job")"
    ts="$(date '+%Y-%m-%dT%H:%M:%S%z')"
    printf '{"job":"%s","status":"processed","processed_at":"%s"}\n' "$job_name" "$ts" > "$DONE_DIR/${job_name%.json}.result.json"
    mv "$job" "$DONE_DIR/$job_name"
  done
done
SCRIPT
  chmod +x "$worker_script"
}

configure_hspanel_systemd() {
  local unit_src="${HSPANEL_INSTALL_DIR}/systemd"
  [[ -d "$unit_src" ]] || return 0

  log_info "  Configuring systemd service units..."

  cat > /etc/systemd/system/hspanel-api.service <<SVC
[Unit]
Description=HostingSignal HS-Panel API
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=root
WorkingDirectory=${HSPANEL_INSTALL_DIR}/developer-panel
ExecStart=${HSPANEL_INSTALL_DIR}/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 3000 --workers 2
Restart=always
RestartSec=5
Environment=PYTHONPATH=${HSPANEL_INSTALL_DIR}/developer-panel
EnvironmentFile=-${HSPANEL_ENV_FILE:-/opt/hostingsignal/deployment/hostingsignal-devapi.production.env}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

  cat > /etc/systemd/system/hspanel-web.service <<SVC
[Unit]
Description=HostingSignal HS-Panel Web UI
After=network.target hspanel-api.service
Wants=hspanel-api.service

[Service]
Type=simple
User=root
WorkingDirectory=${HSPANEL_INSTALL_DIR}/developer-panel/web
Environment=PORT=3001
Environment=HOSTNAME=0.0.0.0
Environment=HSDEV_INTERNAL_API_BASE=http://127.0.0.1:3000
Environment=NEXT_PUBLIC_HSDEV_API_BASE=/devapi
EnvironmentFile=-${HSPANEL_ENV_FILE:-/opt/hostingsignal/deployment/hostingsignal-devapi.production.env}
ExecStart=/usr/bin/node ${HSPANEL_INSTALL_DIR}/developer-panel/web/.next/standalone/server.js
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

  cat > /etc/systemd/system/hspanel-worker.service <<SVC
[Unit]
Description=HostingSignal HS-Panel Worker
After=network.target hspanel-api.service
Wants=hspanel-api.service

[Service]
Type=simple
User=root
WorkingDirectory=${HSPANEL_INSTALL_DIR}
ExecStart=/usr/bin/env bash ${HSPANEL_INSTALL_DIR}/scripts/hspanel_worker.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

  cat > /etc/systemd/system/hspanel-daemon.service <<SVC
[Unit]
Description=HostingSignal HS-Panel Daemon
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
  _configure_ols_panel_proxy
  log_success "  Systemd units configured"
}

_configure_ols_panel_proxy() {
  local httpd_conf="/usr/local/lsws/conf/httpd_config.conf"
  local vh_dir="/usr/local/lsws/conf/vhosts/hs-panel-proxy"
  local vh_conf="${vh_dir}/vhconf.conf"
  local ssl_dir="/etc/hostingsignal/ssl"
  local crt="${ssl_dir}/panel.crt"
  local key="${ssl_dir}/panel.key"

  [[ -f "$httpd_conf" ]] || { log_warning "  OpenLiteSpeed httpd_config.conf not found; skipping panel proxy setup"; return 0; }

  mkdir -p "$vh_dir" "$ssl_dir"

  if [[ ! -f "$crt" || ! -f "$key" ]]; then
    openssl req -x509 -nodes -newkey rsa:2048 \
      -keyout "$key" -out "$crt" -days 3650 \
      -subj "/CN=$(hostname -f 2>/dev/null || hostname)" >/dev/null 2>&1 || true
    chmod 600 "$key" 2>/dev/null || true
  fi

  cat > "$vh_conf" <<EOF
docRoot                   ${HSPANEL_INSTALL_DIR}/frontend

extprocessor hspanel_web {
  type                    proxy
  address                 127.0.0.1:3001
  maxConns                200
  initTimeout             60
  retryTimeout            0
  respBuffer              0
}

extprocessor hspanel_api {
  type                    proxy
  address                 127.0.0.1:3000
  maxConns                200
  initTimeout             60
  retryTimeout            0
  respBuffer              0
}

context /devapi {
  type                    proxy
  handler                 hspanel_api
  addDefaultCharset       off
}

context / {
  type                    proxy
  handler                 hspanel_web
  addDefaultCharset       off
}
EOF

  if ! grep -q "virtualhost hs-panel-proxy" "$httpd_conf"; then
    cat >> "$httpd_conf" <<EOF

virtualhost hs-panel-proxy {
  vhRoot                  ${vh_dir}
  configFile              ${vh_conf}
  allowSymbolLink         1
  enableScript            1
  restrained              1
  vhDomain                _default_
}

listener hspanel_http {
  address                 *:2086
  secure                  0
  map                     hs-panel-proxy *
}

listener hspanel_https {
  address                 *:2087
  secure                  1
  keyFile                 ${key}
  certFile                ${crt}
  map                     hs-panel-proxy *
}
EOF
  fi

  systemctl restart lsws >/dev/null 2>&1 || systemctl restart lshttpd >/dev/null 2>&1 || true
  log_success "  OpenLiteSpeed panel proxy configured on ports 2086/2087"
}

start_hspanel_services() {
  log_info "  Starting native HS-Panel services..."
  systemctl enable --now hspanel-api || log_warning "  hspanel-api failed to start"
  systemctl enable --now hspanel-web || log_warning "  hspanel-web failed to start"
  systemctl enable --now hspanel-worker || log_warning "  hspanel-worker failed to start"
  systemctl enable --now hspanel-daemon || log_warning "  hspanel-daemon failed to start"
  log_success "  HS-Panel services started"
}
