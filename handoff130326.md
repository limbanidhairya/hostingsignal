# Handoff 13-03-2026

## Purpose
This document captures the full AI collaboration flow and the concrete changes implemented during this session, so development can continue without losing context.

## Conversation Narrative (User <-> AI)

1. User provided environment details and asked to proceed with execution in WSL.
2. AI validated available WSL distros and targeted Ubuntu 24.04.
3. AI ran the installer and reported successful completion with minor non-blocking package/repo warnings.
4. User shared that Google Stitch UI designs were available and asked to integrate them.
5. AI imported all Stitch HTML screens and placed them into panel UI locations.
6. User asked to continue the build.
7. AI performed a broad architecture/codebase audit and identified major gaps (stubs, missing layers, incomplete integrations).
8. User requested a full architecture redesign with service-first implementation (CyberPanel-aligned approach).
9. AI started systematic implementation: installer, config, backend service manager modules, and dependency fixes.
10. AI continued implementation across backend, Perl modules, queue/scripts, deployment, and systemd.
11. User asked to deploy before further validation.
12. AI deployed the current stack into WSL Ubuntu 24.04, fixed service unit issues, resolved a legacy daemon port conflict, and verified the live endpoints.

## Major Work Completed

### 1) Installer and Core Configuration
- `install.sh`
	- Rewritten into a universal installer flow for Ubuntu/Debian/Alma/CentOS families.
	- Added staged install functions for webserver, database, mail, DNS, security tools, FTP, docker/git, certbot, and service configuration.
	- Added summary and upgrade handling paths.

- `usr/local/hspanel/config/hspanel.conf`
	- Created comprehensive INI-style config for panel/network/ssl/security/license/webserver/database/mail/dns/ftp/php/docker/backup/logging.

### 2) Dependency Fixes
- `developer-panel/requirements.txt`
	- Expanded to include missing production/backend packages (SQLAlchemy async stack, asyncpg, alembic, redis, pydantic settings, etc.).

- `usr/local/hspanel/backend/requirements.txt`
	- Added backend runtime dependency set for FastAPI/service manager architecture.

### 3) UI Integration (Google Stitch)
- Added imported UI templates to:
	- `usr/local/hspanel/ui/admin_dashboard.html`
	- `usr/local/hspanel/ui/index.html`
	- `usr/local/hspanel/ui/partner_login.html`
	- `usr/local/hspanel/ui/security_gate.html`
	- `usr/local/hspanel/ui/user_dashboard.html`
- Also preserved temporary workspace copies:
	- `tmp_admin_dashboard.html`
	- `tmp_default_index.html`
	- `tmp_login.html`
	- `tmp_security_gate_login.html`
	- `tmp_user_dashboard.html`

### 4) Service Manager Layer (Backend)
Created under `usr/local/hspanel/backend/service_manager/`:

- `base.py`
	- Added `ServiceResult` and `BaseServiceManager` with process/systemctl helpers.

- `webserver.py`
	- OpenLiteSpeed vhost lifecycle and PHP version handling.

- `database.py`
	- MariaDB DB/user lifecycle with grant and password operations.

- `mail.py`
	- Postfix + Dovecot domain/mailbox management and map rebuild support.

- `dns.py`
	- PowerDNS API integration for zone and record management.

- `ssl.py`
	- Certbot-based certificate issue/renew/revoke/list operations.
	- Includes certificate inspection and self-signed panel cert generation support.

### 5) Developer Panel API Rewiring
Updated `developer-panel/api/` to remove major in-memory or mock behavior and route requests through service/database-backed logic.

- `licenses.py`
	- Rewired to `services/license_sync.py` for create/list/info/revoke/stats.
- `plugins.py`
	- Rewired to registry/database-backed operations.
- `updates.py`
	- Rewired to `services/update_publisher.py`.
- `clusters.py`
	- Rewired to managed server models/service logic.
- `auth.py`
	- Replaced session stub flow with DB-backed admin auth and JWT handling.
- `analytics.py`
	- Replaced synthetic values with service-backed aggregates.
- `monitoring.py`
	- Replaced fake metrics with managed server + metric model reads.

### 6) Perl Runtime Completion
Added/fixed key Perl modules under `usr/local/hspanel/perl/HS/`.

- Added:
	- `Domain.pm`
	- `Auth.pm`
	- `Core.pm`
- Upgraded from stubs to operational logic:
	- `Web.pm`
	- `Database.pm`
	- `DNS.pm`
	- `Mail.pm`

### 7) Queue and Script Expansion
- Expanded `usr/local/hspanel/daemon/hs-taskd.pl` to support multiple job types with queue dispatch and result handling.
- Added missing operational scripts under `usr/local/hspanel/scripts/` including:
	- `rebuild_httpd.sh`
	- `rebuild_dns.sh`
	- `rebuild_mail.sh`
	- `rebuild_ftp.sh`
	- `restart_services.sh`
	- `backup_account.sh`
	- `ssl_renew.sh`
	- `quota_sync.sh`
	- `ip_block.sh`
	- `cleanup_tmp.sh`

### 8) Deployment and Runtime Alignment
- Added missing Dockerfiles:
	- `usr/local/hspanel/backend/Dockerfile`
	- `developer-panel/web/Dockerfile`
- Updated `deployment/docker-compose.yml` to point to actual backend/frontend paths and correct runtime ports.
- Updated systemd units under `systemd/` to align with `/usr/local/hspanel` deployment paths.

### 9) WSL Ubuntu 24.04 Deployment
Native deployment was completed and verified inside `Ubuntu-24.04` WSL.

- Source tree mirrored into `/usr/local/hspanel`
- Python virtualenv created at `/usr/local/hspanel/backend/venv`
- Frontend production build created under `/usr/local/hspanel/developer-panel/web/.next`
- Corrected and deployed systemd units for backend and web:
	- `systemd/hostingsignal-api.service`
	- `systemd/hostingsignal-web.service`
- Verified running services:
	- `hostingsignal-api.service`
	- `hostingsignal-web.service`
	- `hostingsignal-daemon.service`
	- `hostingsignal-taskd.service`
- Verified endpoints from both WSL and Windows host:
	- `http://localhost:2083/health`
	- `http://localhost:3000`
	- `http://localhost:2086`
- Resolved legacy conflict by disabling old `cpsrvd.service` from `/usr/local/hostingsignal`, which had been occupying port `2086`.

### 10) Systemd Unit Corrections
- `systemd/hostingsignal-api.service`
	- Fixed `WorkingDirectory` to `/usr/local/hspanel`
	- Fixed `PYTHONPATH` to `/usr/local/hspanel`
	- Fixed app import target to `backend.api.main:app`
- `systemd/hostingsignal-web.service`
	- Replaced `npm run start` with direct standalone server execution:
	- `node /usr/local/hspanel/developer-panel/web/.next/standalone/server.js`
	- Added `HOSTNAME=0.0.0.0`

## Files Added/Changed (Session)

- `install.sh` (rewritten)
- `developer-panel/requirements.txt` (updated)
- `usr/local/hspanel/config/hspanel.conf` (new)
- `usr/local/hspanel/backend/requirements.txt` (new)
- `usr/local/hspanel/backend/service_manager/base.py` (new)
- `usr/local/hspanel/backend/service_manager/webserver.py` (new)
- `usr/local/hspanel/backend/service_manager/database.py` (new)
- `usr/local/hspanel/backend/service_manager/mail.py` (new)
- `usr/local/hspanel/backend/service_manager/dns.py` (new)
- `usr/local/hspanel/backend/service_manager/ssl.py` (new)
- `developer-panel/api/licenses.py` (updated)
- `developer-panel/api/plugins.py` (updated)
- `developer-panel/api/updates.py` (updated)
- `developer-panel/api/clusters.py` (updated)
- `developer-panel/api/auth.py` (updated)
- `developer-panel/api/analytics.py` (updated)
- `developer-panel/api/monitoring.py` (updated)
- `usr/local/hspanel/perl/HS/Domain.pm` (new)
- `usr/local/hspanel/perl/HS/Auth.pm` (new)
- `usr/local/hspanel/perl/HS/Core.pm` (new)
- `usr/local/hspanel/perl/HS/Web.pm` (updated)
- `usr/local/hspanel/perl/HS/Database.pm` (updated)
- `usr/local/hspanel/perl/HS/DNS.pm` (updated)
- `usr/local/hspanel/perl/HS/Mail.pm` (updated)
- `usr/local/hspanel/daemon/hs-taskd.pl` (updated)
- `usr/local/hspanel/scripts/*.sh` operational scripts (new)
- `usr/local/hspanel/backend/Dockerfile` (new)
- `developer-panel/web/Dockerfile` (new)
- `deployment/docker-compose.yml` (updated)
- `systemd/hostingsignal-api.service` (updated)
- `systemd/hostingsignal-web.service` (updated)
- `systemd/hostingsignal-daemon.service` (updated/aligned)
- `systemd/hostingsignal-taskd.service` (new)
- `systemd/hostingsignal-monitor.service` (updated/aligned but not deployed in WSL)
- `usr/local/hspanel/ui/*.html` mapped Stitch screens (updated/new)
- `tmp_*.html` Stitch staging files (updated)
- `handoff130326.md` (updated, this document)

## Current Runtime State

### Verified in WSL
- Backend health endpoint is live on `2083`.
- Frontend is live on `3000`.
- Perl daemon UI is live on `2086`.
- Task daemon is active and watching `/var/hspanel/queue`.

### Known Runtime Caveats
- `hostingsignal-monitor.service` was not deployed because `append_system_monitor.py` in the repo root is a Windows-side patch script, not a Linux runtime monitor entrypoint.
- The root `install.sh` still behaves primarily as package/config orchestration and does not by itself mirror the repo into `/usr/local/hspanel`; that copy/sync step was performed manually during WSL deployment.

## Pending Work (Not Yet Implemented)

- Implement a proper Linux monitor service entrypoint and enable `hostingsignal-monitor.service`.
- Fold the WSL/native deploy sync step into a reproducible installer/deploy command so `/usr/local/hspanel` is populated automatically.
- Perform deeper end-to-end validation across API routes, queue jobs, and service-manager operations.
- Decide whether the older `/usr/local/hostingsignal` tree should be removed or kept isolated; its legacy services can conflict with the new deploy.
- Clean up any remaining environment-specific assumptions in service units or scripts discovered during WSL/native runtime validation.

## Notes
- Sensitive credentials shared during setup are intentionally omitted/redacted from this handoff document.
- This handoff is intended as a direct continuation point for implementation.
- The current highest-confidence continuation point is the live WSL Ubuntu 24.04 deployment under `/usr/local/hspanel`.

---

## Addendum: Partner Portal + WHMCS Phase (Post Initial Handoff)

### Scope Completed in This Addendum

1. Developer/Partner auth flow moved to real backend JWT flow and validated against `/api/auth/me`.
2. Dashboard navigation pages connected to backend APIs for stats/software/plugin catalog.
3. Built-in plugin catalog added with plan-aware gating and admin override support:
	- Open Source Vulnerability Scanner
	- WordPress Manager
	- Node App Manager
	- React App Manager
	- Python App Manager
	- Docker Service Manager
	- WHMCS Billing Integration Addon
4. WHMCS integration implemented in three layers:
	- API callbacks under `/api/whmcs/*`
	- Queue-backed lifecycle execution via `hs-taskd.pl`
	- WHMCS server/addon module scaffolds under `usr/local/hspanel/plugins/whmcs-addon/`
5. Product-level WHMCS mapping persistence added (product ID -> plan/package/plugins/admin_override).
6. Partner portal redirect loop hardening completed:
	- Login validates token before redirect.
	- Dashboard only logs out on real auth failure.
	- API fallback supports same-origin proxy and direct host fallback.
7. UI load responsiveness improved by:
	- Non-blocking dashboard data boot after auth success.
	- Analytics license lookup timeout.
	- Software endpoint timeout reduction + short cache.

### Key Files Updated in This Addendum

- `developer-panel/web/src/app/login/page.js`
- `developer-panel/web/src/app/page.js`
- `developer-panel/web/next.config.js`
- `developer-panel/api/plugins.py`
- `developer-panel/api/whmcs.py`
- `developer-panel/api/analytics.py`
- `developer-panel/api/software.py`
- `developer-panel/api/config.py`
- `developer-panel/api/main.py`
- `usr/local/hspanel/daemon/hs-taskd.pl`
- `usr/local/hspanel/scripts/whmcs_provision.sh`
- `usr/local/hspanel/plugins/whmcs-addon/modules/servers/hostingsignal_whmcs/hostingsignal_whmcs.php`
- `usr/local/hspanel/plugins/whmcs-addon/modules/addons/hostingsignal_whmcs/hostingsignal_whmcs.php`
- `usr/local/hspanel/plugins/whmcs-addon/README.txt`

### Runtime Walkthrough (Operational)

#### 1) Service Health (WSL)

Verify all required services are active:

- `systemctl status hostingsignal-devapi`
- `systemctl status hostingsignal-web`
- `systemctl status hostingsignal-taskd`

Required outcomes:

- Dev API listening on `2087`
- Web app listening on `3000`
- Task daemon watching `/var/hspanel/queue`

#### 2) Partner Portal Login Path

Open:

- `http://localhost:3000/login`

Flow:

1. Login submits to `/devapi/api/auth/login` (or fallback host `:2087` if needed).
2. Token is stored as `hsdev_token`.
3. Session is immediately validated via `/api/auth/me`.
4. On success, redirect to `/`.
5. Dashboard loads non-critical data asynchronously to avoid auth-loop regressions.

#### 3) WHMCS API Callback Path

Endpoints (token protected via `X-HS-WHMCS-Token`):

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

#### 4) Queue Execution Path for WHMCS Lifecycle

1. `/api/whmcs/provision/*` writes job JSON files to `/var/hspanel/queue`.
2. `hs-taskd.pl` picks jobs and dispatches to `whmcs_provision.sh`.
3. Completed jobs move to `/var/hspanel/queue/done` with `.result.json` records.
4. Service state is persisted at `/var/hspanel/userdata/whmcs_services/<service_id>.json`.

#### 5) WHMCS Product Mapping Flow

1. Upsert mapping with `product_id` + `plan` + `package_name` + plugin slugs.
2. CreateAccount with `whmcs_product_id` auto-resolves mapping.
3. If mapping exists, it overrides fallback payload values.
4. If mapping absent, fallback payload is used.

### Troubleshooting Walkthrough

#### Partner Login Redirect Loop

If user still loops to login:

1. Hard refresh browser (`Ctrl+F5`).
2. Check `/devapi/api/health` from browser host.
3. Verify `/api/auth/login` and `/api/auth/me` via proxy on port `3000`.
4. Confirm stale invalid token is removed from browser local storage (`hsdev_token`).

#### Slow Dashboard Load

1. Check latency for:
	- `/devapi/api/analytics/stats`
	- `/devapi/api/software/list`
2. Confirm analytics timeout is active and API stays responsive when license server is slow.
3. Confirm software endpoint cache is returning quickly on repeat requests.

### Current Known Gaps (After Addendum)

1. WHMCS module scaffold is functional but still minimal for production UX (no full WHMCS-side product wizard).
2. No HMAC request signing yet; current callback protection is shared token only.
3. No centralized audit UI yet for WHMCS mapping changes and lifecycle events.

### Immediate Next Recommended Steps

1. Add HMAC signing + replay protection to WHMCS callbacks.
2. Add audit log persistence/reporting for provisioning and mapping events.
3. Add partner dashboard page for WHMCS product mappings to avoid API/manual dependency.
