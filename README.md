<p align="center">
  <img src="developer-panel/web/public/branding/hostingsignal-logo.png" alt="HostingSignal Logo" width="190" />
</p>

<h1 align="center">HostingSignal</h1>

<p align="center">
  Service-first hosting control platform with Partner Panel, WHMCS integration, queue orchestration, and production-ready runtime hardening.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-1f6feb?style=for-the-badge" />
  <img alt="Release" src="https://img.shields.io/badge/release-v1.0.0-0f766e?style=for-the-badge" />
  <img alt="API" src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge" />
  <img alt="Web" src="https://img.shields.io/badge/Web-Next.js-111827?style=for-the-badge" />
</p>

## Latest Project Status (March 15, 2026)

- Current release tag: `v1.0.0`
- Release branch: `release/2026-03-15-rc1`
- Core runtime checks were validated across ports `2083`, `2086`, `2087`, and `3000`
- Launch preflight reached `critical_failures=0` in release path
- Release process and merge governance docs are in `docs/release_scope_2026-03-15.md` and `docs/merge_checklist_2026-03-15.md`

## Monorepo Layout

```text
Hostingsignal/
|- developer-panel/
|  |- api/                 # FastAPI partner/dev API
|  |- services/            # Analytics, cluster, updates, license sync
|  |- web/                 # Next.js partner portal
|- license-server/         # Licensing service
|- usr/local/hspanel/      # Core daemon, scripts, plugins, templates
|- deployment/             # Compose, manifests, deployment helpers
|- systemd/                # Linux service units
`- docs/                   # Architecture and release docs
```

## Core Services

| Service | Port | Purpose |
|---|---:|---|
| `hostingsignal-web` | `3000` | Next.js partner panel |
| `hostingsignal-devapi` | `2087` | Partner/developer FastAPI |
| `hostingsignal-daemon` | `2086` | Core daemon panel APIs |
| `hostingsignal-api` | `2083` | Core backend API |
| `hostingsignal-taskd` | n/a | Queue worker and lifecycle execution |

## Local Runtime Endpoints

- Partner login: `http://localhost:3000/login`
- Partner dashboard: `http://localhost:3000/`
- Dev API health: `http://localhost:2087/api/health`
- Dev API docs: `http://localhost:2087/api/docs`
- Proxy health via web: `http://localhost:3000/devapi/api/health`

## Key Platform Capabilities

- WHMCS callbacks for create/suspend/unsuspend/terminate lifecycle actions
- Product mapping support (`product_id -> package/plan/plugins/admin_override`)
- Queue-based orchestration through `/var/hspanel/queue`
- Admin-protected internal orchestration routes under `/internal/services/*`
- Launch readiness and hardening checks via `/api/system/preflight`

## Service-First Installer

Canonical installer is repository root `install.sh`.

```bash
# Stage
sudo ./install.sh --mode stage --local-root ./local/services

# Install
sudo ./install.sh --mode install --db-engine mariadb --web-stack openlitespeed

# Configure
sudo ./install.sh --mode configure --local-root ./local/services
```

## Quick Operations

```bash
# WSL service state
sudo systemctl status hostingsignal-devapi
sudo systemctl status hostingsignal-web
sudo systemctl status hostingsignal-taskd

# Restart API and web
sudo systemctl restart hostingsignal-devapi
sudo systemctl restart hostingsignal-web

# Build Next.js standalone bundle (when running from deployed path)
cd /usr/local/hspanel/developer-panel/web
npm run build
```

## Branding

- Source logo: `developer-panel/web/public/branding/hostingsignal-logo.png`
- Runtime path: `/branding/hostingsignal-logo.png`

## Docs and GitHub Pages (Prepared)

This repository now includes a GitHub Pages workflow for documentation publishing.

- Workflow: `.github/workflows/docs-pages.yml`
- Docs root for Pages: `docs/`
- Docs landing page: `docs/index.md`

### Planned Production Publish

When you share server details and domain, we will finalize:

1. `Settings -> Pages` source/permissions verification
2. Custom domain (`CNAME`) setup
3. DNS records (`A`/`ALIAS`/`CNAME`) for your domain
4. Optional reverse-proxy/server mirror if you want docs served from your own host as well

Default Pages URL pattern will be:

```text
https://<owner>.github.io/hostingsignal/
```

## Release and Process Docs

- `docs/release_scope_2026-03-15.md`
- `docs/merge_checklist_2026-03-15.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `docs/handoff_2026-03-15.md`

## License

Internal project. Add formal license text before public redistribution.
