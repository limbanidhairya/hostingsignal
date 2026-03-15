---
title: Release Scope 2026-03-15
permalink: /release_scope_2026-03-15/
---

# Release Scope Review - 2026-03-15

This file classifies the current working tree into release-ready changes versus changes that should be intentionally reviewed before being included in a GitHub release.

## Summary

- Runtime health is good on ports 2083, 2086, 2087, and 3000.
- Devpanel launch preflight is green for critical checks.
- The repository is still broad in scope: 94 changed entries remain.
- The current tree mixes release-hardening, UI/runtime fixes, backend feature work, installer work, test artifacts, and documentation drafts.

## Ship Now

These changes are directly tied to the currently validated runtime and release hardening.

### Release hardening

- `.gitignore`
- `deployment/docker-compose.yml`
- `deployment/init-db.sh`
- `developer-panel/Dockerfile`
- `developer-panel/api/config.py`
- `developer-panel/api/database.py`
- `developer-panel/api/main.py`
- `developer-panel/api/system.py`
- `developer-panel/api/containers.py`
- `developer-panel/api/internal_services.py`
- `developer-panel/api/shell.py`
- `developer-panel/services/local_monitor.py`

Reason:
These files are part of the validated production-style devpanel path: Postgres-backed startup, hardened env behavior, optional router resilience, and launch preflight support.

### 2086 daemon and template fixes

- `usr/local/hspanel/daemon/hs-srvd.pl`
- `usr/local/hspanel/templates/ui/master.tmpl`
- `usr/local/hspanel/templates/ui/default_index.tmpl`
- `usr/local/hspanel/ui/index.html`
- `tmp_default_index.html`

Reason:
These files contain the directly verified 2086 fixes: responsive shell behavior, header interaction logic, conditional rendering fixes, keyboard support, and removal of the unwanted top header from the unconfigured page.

### 3000 web shell and session routing

- `developer-panel/web/src/app/page.js`
- `developer-panel/web/src/app/login/page.js`
- `developer-panel/web/src/app/layout.js`
- `developer-panel/web/src/app/globals.css`
- `developer-panel/web/next.config.js`
- `developer-panel/web/src/middleware.js`
- `developer-panel/web/src/app/api/session/login/route.js`
- `developer-panel/web/src/app/api/session/logout/route.js`
- `developer-panel/web/src/app/api/session/me/route.js`
- `developer-panel/web/src/app/api/session/token/route.js`
- `developer-panel/web/src/app/auth/login/page.js`
- `developer-panel/web/public/branding/hostingsignal-logo.png`

Reason:
These files are part of the validated 3000 login/session flow and responsive dashboard shell currently running in Docker.

### Route alias pages for the existing dashboard shell

- `developer-panel/web/src/app/analytics/page.js`
- `developer-panel/web/src/app/backups/page.js`
- `developer-panel/web/src/app/clusters/page.js`
- `developer-panel/web/src/app/containers/page.js`
- `developer-panel/web/src/app/docker/page.js`
- `developer-panel/web/src/app/domains/page.js`
- `developer-panel/web/src/app/email/page.js`
- `developer-panel/web/src/app/files/page.js`
- `developer-panel/web/src/app/licenses/page.js`
- `developer-panel/web/src/app/monitoring/page.js`
- `developer-panel/web/src/app/plugins/page.js`
- `developer-panel/web/src/app/security/page.js`
- `developer-panel/web/src/app/shell/page.js`
- `developer-panel/web/src/app/updates/page.js`
- `developer-panel/web/src/app/whmcs-audit/page.js`

Reason:
These are thin aliases into the main app shell and are consistent with the session/middleware routing model already in use.

## Review Before Ship

These changes may be valid, but they broaden the release beyond the currently verified release-hardening work.

### Backend feature and compatibility expansion

- `usr/local/hspanel/backend/api/*.py`
- `usr/local/hspanel/backend/service_manager/*.py`
- `usr/local/hspanel/backend/Dockerfile`
- `usr/local/hspanel/perl/HS/Database.pm`
- `usr/local/hspanel/perl/HS/Mail.pm`
- `usr/local/hspanel/perl/HS/Web.pm`
- `usr/local/hspanel/perl/HS/Cron.pm`
- `usr/local/hspanel/perl/HS/Ftp.pm`
- `usr/local/hspanel/templates/ui/databases.tmpl`
- `usr/local/hspanel/templates/ui/email.tmpl`
- `usr/local/hspanel/templates/ui/domains.tmpl`
- `usr/local/hspanel/templates/ui/backups.tmpl`
- `usr/local/hspanel/templates/ui/login.tmpl`
- `usr/local/hspanel/backend/api/compat.py`

Reason:
This group is larger backend and panel functionality work. Prior reports show these flows tested well, but this is still a major feature block and should be shipped intentionally, not accidentally.

### WHMCS and developer-panel feature work

- `developer-panel/api/auth.py`
- `developer-panel/api/clusters.py`
- `developer-panel/api/monitoring.py`
- `developer-panel/api/whmcs.py`
- `developer-panel/services/cluster_manager.py`
- `developer-panel/services/license_sync.py`
- `developer-panel/requirements.txt`
- `cli/hsctl.py`
- `usr/local/hspanel/plugins/whmcs-addon/README.txt`
- `usr/local/hspanel/plugins/whmcs-addon/modules/addons/hostingsignal_whmcs/hostingsignal_whmcs.php`
- `usr/local/hspanel/plugins/whmcs-addon/modules/servers/hostingsignal_whmcs/hostingsignal_whmcs.php`

Reason:
These files change feature behavior and integration surfaces beyond the narrow release-hardening scope.

### Installer and local sandbox scaffolding

- `install.sh`
- `configs/`
- `core/`
- `scripts/`
- `services/`
- `tests/`
- `systemd/hostingsignal-devapi.service`
- `systemd/hostingsignal-recovery.service`
- `systemd/hostingsignal-recovery.timer`

Reason:
This is substantial new installer and local stack functionality. It should be released as its own scoped feature set or milestone, not bundled implicitly with runtime hotfixes.

## Do Not Use As Release Inputs

These files are documentation snapshots or local planning outputs and should not be treated as required runtime content for the release.

- `docs/build_status_iteration_2026-03-15.md`
- `docs/handoff_2026-03-15.md`
- `docs/local_services_installer.md`
- `PROJECT_STRUCTURE.md`
- `README.md`

Reason:
These are useful references, but they are not required for the application to run and some are clearly iteration-specific notes.

## Recommendation

For the next GitHub release, create a narrow release branch containing only:

1. Release hardening files.
2. 2086 daemon/template fixes.
3. 3000 session/routing/responsive shell files.

Then review the remaining backend, installer, WHMCS, and documentation changes as separate follow-up batches.