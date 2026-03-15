<p align="center">
  <img src="https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/frontend/public/logo.png" alt="HostingSignal Logo" width="180" onerror="this.src='https://via.placeholder.com/180?text=HostingSignal'"/>
</p>

<h1 align="center">🚀 HostingSignal Panel</h1>

<p align="center">
  <strong>⚡ Service-First Hosting Control Platform with Partner Portal + WHMCS Integration</strong>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/Version-1.0.0-2563eb?style=for-the-badge&logo=semantic-release">
  <img alt="Backend FastAPI" src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi">
  <img alt="Frontend Next.js" src="https://img.shields.io/badge/Web-Next.js-black?style=for-the-badge&logo=next.js">
  <img alt="WHMCS" src="https://img.shields.io/badge/Billing-WHMCS%20Addon-0ea5e9?style=for-the-badge&logo=php">
  <img alt="Queue" src="https://img.shields.io/badge/Queue-hs--taskd-f59e0b?style=for-the-badge&logo=gnubash">
</p>

---

## 🧭 Overview
HostingSignal is a modern control panel stack with:

- 🖥️ Partner/developer web panel (`developer-panel/web`)
- 🔐 JWT auth API (`developer-panel/api`)
- 📦 Plugin marketplace with plan-based gating + admin override
- 💳 WHMCS server/addon module integration
- 🧵 Queue-based execution daemon (`hs-taskd`) for lifecycle tasks
- 🧰 Service-first Linux stack under `/usr/local/hspanel`

## 🏗️ Current Architecture (Live)

```text
Hostingsignal/
├── developer-panel/
│   ├── api/                          # FastAPI (auth, analytics, plugins, whmcs, etc.)
│   ├── services/                     # Registry, cluster, analytics, update, license sync
│   └── web/                          # Next.js 14 partner portal
├── license-server/                   # License API service
├── usr/local/hspanel/
│   ├── daemon/hs-taskd.pl            # Queue processor
│   ├── scripts/                      # Provision/maintenance scripts
│   ├── perl/HS/                      # Perl service modules
│   └── plugins/whmcs-addon/          # WHMCS server + addon module scaffold
├── systemd/                          # Service unit definitions
├── deployment/                       # docker-compose + k8s manifests
└── install.sh                        # Service-first installer
```

## 🌐 Live Endpoints (Local Runtime)

- 🟢 Partner Login: `http://localhost:3000/login`
- 🟢 Partner Dashboard: `http://localhost:3000/`
- 🟢 Dev API Health: `http://localhost:2087/api/health`
- 🟢 Dev API Docs: `http://localhost:2087/api/docs`
- 🟢 Web-proxy API Health: `http://localhost:3000/devapi/api/health`

## 🔐 Authentication Notes

- Server session cookie key: `hsdev_session` (HTTP-only)
- Login/session endpoints:
  - `POST /api/session/login`
  - `GET /api/session/me`
  - `POST /api/session/logout`
  - `GET /api/session/token`
- Middleware route guard enforces session before `/` dashboard access.
- Legacy local token key `hsdev_token` is still mirrored for API authorization headers.

## 🎨 Branding Notes

- Primary logo asset: `developer-panel/web/public/branding/hostingsignal-logo.png`
- Runtime logo path: `/branding/hostingsignal-logo.png`
- Current UI palette is aligned to brand blues in `developer-panel/web/src/app/layout.js` and `developer-panel/web/src/app/globals.css`.

## 🧩 Built-in Plugin Catalog

- 🛡️ Open Source Vulnerability Scanner
- 🧱 WordPress Manager
- 🟢 Node App Manager
- ⚛️ React App Manager
- 🐍 Python App Manager
- 🐳 Docker Service Manager
- 💳 WHMCS Billing Integration Addon

Plan logic:

- 📈 Tiered plans: `starter`, `professional`, `business`, `enterprise`
- 🔒 Premium plugins require higher plan
- 👑 `admin_override=true` can enable premium plugin on lower plan during package creation

## 💳 WHMCS Integration (Implemented)

### Server Module Callbacks

- `CreateAccount`
- `SuspendAccount`
- `UnsuspendAccount`
- `TerminateAccount`
- `TestConnection`

### WHMCS API Endpoints

- `/api/whmcs/health`
- `/api/whmcs/package/sync`
- `/api/whmcs/provision/create-account`
- `/api/whmcs/provision/suspend-account`
- `/api/whmcs/provision/unsuspend-account`
- `/api/whmcs/provision/terminate-account`
- `/api/whmcs/product-mappings`
- `/api/whmcs/product-mappings/upsert`
- `/api/whmcs/product-mappings/resolve`
- `/api/whmcs/product-mappings/delete`

### Product Mapping Capability

WHMCS `product_id` can map to:

- package name
- plan
- plugin list
- admin override flag

Provisioning auto-resolves mapping when `whmcs_product_id` is sent.

## 🧵 Queue + Daemon Execution Flow

1. WHMCS callback hits `/api/whmcs/provision/*`
2. API writes queue job to `/var/hspanel/queue/*.json`
3. `hostingsignal-taskd` picks job and dispatches action
4. Script `whmcs_provision.sh` executes lifecycle state change
5. Results written to `/var/hspanel/queue/done/*.result.json`
6. Service state stored at `/var/hspanel/userdata/whmcs_services/<service_id>.json`

## ⚙️ Service-First Install

Universal one-command install for the full local stack:

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

Core-only fallback:

```bash
bash ./install.sh --non-interactive --profile-set core --web openlitespeed --db mariadb
```

This command renders the compose stack, writes service workspaces, persists `configs/install-config.json`, and starts the selected full profile set in one run.

## 🧪 Runtime Commands

```bash
# WSL service checks
sudo systemctl status hostingsignal-devapi
sudo systemctl status hostingsignal-web
sudo systemctl status hostingsignal-taskd

# Rebuild and restart web
cd /usr/local/hspanel/developer-panel/web
npm run build
sudo systemctl restart hostingsignal-web

# Restart API
sudo systemctl restart hostingsignal-devapi

# Container runtime quick checks
hsctl container status
hsctl container list

# DNS replication checks
hsctl dns verify --zone example.com

# Deploy current iteration to WSL target and run verification
sudo bash scripts/deploy_iteration_wsl.sh

# Fix Docker socket permissions in WSL for container runner
sudo bash scripts/fix_container_runtime_permissions_wsl.sh

# Show current dev API test credentials and verify login
sudo bash scripts/get_test_credentials_wsl.sh --verify
```

## 🚀 Launch Hardening (2-Day Checklist)

Generate a hardened HSDEV env file:

```bash
cd /usr/local/hspanel
bash scripts/generate_production_env.sh
```

Then:

1. Edit `deployment/hostingsignal-devapi.production.env` and replace placeholders:
  - `CHANGE_DB_PASSWORD`
  - `CHANGE_LICENSE_API_KEY`
  - `HSDEV_WHMCS_ALLOWED_IPS`
2. Apply it to the running WSL service (creates systemd drop-in + restarts safely):

```bash
cd /usr/local/hspanel
sudo bash scripts/apply_devapi_production_env_wsl.sh
```

3. Verify launch readiness from dashboard preflight (`/api/system/preflight`).

## 📋 Systemd Services

| Service | Purpose | Port |
|---|---|---|
| `hostingsignal-devapi` | Partner/Developer API (FastAPI) | `2087` |
| `hostingsignal-web` | Partner portal (Next.js standalone) | `3000` |
| `hostingsignal-taskd` | Queue processor (Perl daemon) | n/a |
| `hostingsignal-daemon` | Core panel daemon | `2086` |
| `hostingsignal-api` | Core API service | `2083` |

## 🛠️ Troubleshooting Quick Guide

### 🔁 Login Redirect Loop

1. Open `http://localhost:3000/login`
2. Hard refresh (`Ctrl+F5`)
3. Verify proxy API health: `http://localhost:3000/devapi/api/health`
4. Verify direct API health: `http://localhost:2087/api/health`

### 🐢 Slow Dashboard

Check endpoint timings:

```bash
curl -s -o /dev/null -w "stats=%{time_total}\n" http://localhost:3000/devapi/api/analytics/stats
curl -s -o /dev/null -w "software=%{time_total}\n" http://localhost:3000/devapi/api/software/list
```

Expected: sub-second responses in healthy local runtime.

## 📚 Key Docs

- `handoff130326.md` (latest implementation + runbook)
- `docs/06_cyberpanel_aligned_approach.md`
- `docs/05_queue_security_plugins_microservices.md`
- `docs/index.md`
- `docs/admin_reference.md`
- `docs/local_services_installer.md`

## 🌍 Documentation Site

Configured custom docs domain:

```text
https://docs.hostingsignal.in/
```

Admin reference landing page:

```text
https://docs.hostingsignal.in/admin_reference.html
```

---

<p align="center">
  🛡️ Built with care by the HostingSignal team • ⚙️ Service-first • 🚀 Production-focused
</p>
