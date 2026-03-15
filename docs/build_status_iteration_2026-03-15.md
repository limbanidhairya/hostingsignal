# Build Status Iteration - 2026-03-15

## Completed Modules
- Core orchestration scaffolding in core/orchestrator
- Service registry with startup dependency order
- Internal service orchestration API routes in developer API
- cPanel-style hsctl service subcommands
- WSL environment test loop script

## Modules In Progress
- DNS cluster implementation logic
- Container runner implementation logic
- Recovery manager active restart loop implementation
- Service-specific integration tests (mail, dns, ftp functional flows)

## Modules Missing
- Full panel/frontend and panel/backend canonical split under panel/
- Dedicated service folders for every stack component with runtime/config/data/log segregation
- End-to-end mail and dns functional automation
- Production secrets bootstrap automation in systemd environment files

## Errors Detected
- None in source validation for newly added files

## Fixes Applied
- Added dependency-aware orchestrator module and internal API
- Added hsctl service command group for start/stop/restart/status
- Added scripts/test_environment.sh for repeated WSL validation

## Next Steps
1. Run test_environment.sh in WSL and collect failure points.
2. Add orchestrator-backed restart policy engine under core/recovery-manager.
3. Implement dns-cluster sync and health checks with config-driven master/slave roles.
4. Add production env file wiring and lock down default secrets before launch.

---

## Iteration Update (same day)

### Completed Modules
- Added executable recovery manager in `core/recovery-manager/recovery_manager.py`.
- Added DNS cluster status/sync script in `core/dns-cluster/sync.sh`.
- Added `hsctl dns status|sync` and `hsctl recovery run-once|status` commands.
- Expanded WSL test script with orchestrator/recovery/DNS script checks.

### Validation Results
- WSL environment test: `HEALTHY (12 checks passed)`.
- Internal orchestrator API validated over localhost proxy.
- `hsctl dns status` and `hsctl recovery run-once` validated from WSL.

### Current Runtime Risks
- Remaining launch blockers for this iteration: none in WSL runtime test loop.

### Runtime Fixes Applied
- Installed and enabled `memcached`.
- Installed `dnsutils` (provides `dig`).
- Added `core/dns-cluster/configure_wsl.sh` and applied WSL-safe PowerDNS config:
	- DNS listener moved to `127.0.0.1:5300`
	- PowerDNS web/API enabled on `127.0.0.1:8053`
- Fixed line-ending portability in deployed scripts (`sed -i 's/\r$//'`).

### Latest Validation
- WSL environment test: `HEALTHY (14 checks passed)`.
- PowerDNS API listener confirmed on `127.0.0.1:8053`.
- Recovery manager run-once and hsctl dns/recovery command groups execute successfully.

### Distributed License Runtime (Implemented)
- Added executable client: `core/license-client/license_client.py`.
- Added system API endpoints:
	- `POST /api/system/license/cache-key`
	- `GET /api/system/license/runtime-status`
- Added config options in developer API:
	- `HSDEV_LICENSE_VALIDATE_PATH`
	- `HSDEV_LICENSE_CACHE_PATH`
	- `HSDEV_LICENSE_GRACE_HOURS`

### Distributed License Validation Result
- Cache key write endpoint works and persists to `/usr/local/hspanel/configs/license.cache`.
- Runtime status endpoint returns structured failover state when central API is unreachable (`status=unreachable` without grace window).

### Recovery Scheduling (Implemented)
- Added systemd unit: `systemd/hostingsignal-recovery.service`.
- Added systemd timer: `systemd/hostingsignal-recovery.timer`.
- Timer enabled in WSL runtime (`hostingsignal-recovery.timer` active), executing one-shot recovery cycles every 30 seconds.

### Dashboard Runtime Visibility (Implemented)
- Dashboard now displays distributed license runtime source/status/grace details from `/api/system/license/runtime-status`.

### Latest Validation Snapshot
- Localhost login endpoint healthy: HTTP 200.
- Internal preflight and license runtime endpoints healthy through `/devapi` proxy.
- WSL environment test script now passes 16 checks (`HEALTHY`).

### Launch Hardening Automation (Implemented)
- Added env support for distributed licensing values in API config:
	- `HSDEV_LICENSE_SERVER_URL`
	- `HSDEV_LICENSE_API_KEY`
- Added `scripts/generate_production_env.sh` to generate hardened production env file with:
	- random JWT secret
	- random bootstrap admin password
	- random WHMCS shared/HMAC secrets
	- production mode enabled
	- PostgreSQL DSN placeholder (non-SQLite baseline)
- Added systemd unit template `systemd/hostingsignal-devapi.service` with optional `EnvironmentFile` support.
- Added `scripts/apply_devapi_production_env_wsl.sh` to:
	- copy env file to `/etc/hostingsignal/hostingsignal-devapi.env`
	- create drop-in override under `/etc/systemd/system/hostingsignal-devapi.service.d/override.conf`
	- daemon-reload + restart + health check the live dev API service
- Updated README with launch hardening checklist using generated env + preflight verification flow.

### Container Runner (Implemented)
- Added executable runtime module: `core/container-runner/container_runner.py`.
- Added secured container API router: `developer-panel/api/containers.py`.
- Mounted container routes in `developer-panel/api/main.py` under `/api/containers/*`.
- Added `hsctl container` command group:
	- `status`
	- `list`
	- `run`
	- `start`
	- `stop`
	- `remove`
	- `logs`
- Expanded WSL environment checks to assert container runner script presence.
- Added web dashboard `Containers` view with runtime availability and container inventory table.

### DNS Replication Verification (Implemented)
- Upgraded `core/dns-cluster/sync.sh` with `verify` mode.
- `verify` performs SOA serial comparisons between master and configured slave nodes.
- Returns non-zero on drift/no-response to support CI/automation gating.
- Added `hsctl dns verify --zone <domain>` command.

### Preflight Coverage Extension (Implemented)
- Launch preflight now includes `container_runtime_access` warning check.
- Detects missing runtime or inaccessible Docker/Podman daemon before launch.
- Container runner now returns actionable hint when Docker socket permission is denied.

### WSL Iteration Deployment Automation (Implemented)
- Added `scripts/deploy_iteration_wsl.sh` for one-command rollout of this iteration to `/usr/local/hspanel`.
- Script copies updated API/core/web/CLI files, rebuilds web, restarts services, and verifies:
	- `/api/health`
	- login + `/api/system/preflight`
	- `/api/containers/status`
	- full `scripts/test_environment.sh` loop

### Container Runtime Permission Automation (Implemented)
- Added `scripts/fix_container_runtime_permissions_wsl.sh`.
- Script ensures `docker` group exists, adds target user, restarts docker service, and verifies `docker info` access.

### Test Reliability Hardening (Implemented)
- Updated `scripts/test_environment.sh` to use per-run `mktemp` files with cleanup trap.
- Eliminates prior `/tmp/hs_test.out` ownership collision causing false-negative failures in non-root runs.

### Test Credential Utility (Implemented)
- Added `scripts/get_test_credentials_wsl.sh`.
- Reads effective dev API bootstrap credentials from `/etc/hostingsignal/hostingsignal-devapi.env` with safe defaults.
- Optional `--verify` mode performs live login against `http://127.0.0.1:2087/api/auth/login`.

### Next Steps
1. Implement distributed license runtime flow in `core/license-client` using `configs/license.cache` with 72-hour grace period.
2. Add recovery manager systemd unit/timer for continuous 30-second loops.
3. Add functional DNS replication test targets and slave verification IPs for non-placeholder cluster nodes.
4. Begin container-runner executable support for Docker/Podman service lifecycle.
