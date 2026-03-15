---
title: Local Services Installer
permalink: /local_services_installer/
---

# Local Services Installer

This installer replaces the previous `/usr/local`-centric flow with a repository-local sandbox.

## Goals
- Keep service definitions, compose topology, config templates, and installer logic in Git.
- Materialize local service workspaces under `services/`.
- Keep mutable runtime data under `data/`, `runtime/`, and `logs/local-services/`.
- Support WSL Ubuntu 24.04 and standard Linux hosts with Docker + Docker Compose.

## Entry Point

```bash
./install.sh
```

## Universal One-Command Install

The installer now supports a true full-stack one-command run that generates config, renders compose assets, writes service workspaces, and starts all configured profiles.

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

Core-only fallback:

```bash
bash ./install.sh --non-interactive --profile-set core --web openlitespeed --db mariadb
```

Interactive selections:
- Web server: OpenLiteSpeed or Apache
- Database: MariaDB or MySQL

Selections are stored in:
- `configs/install-config.json`

## Generated Layout

```text
services/
configs/
logs/local-services/
runtime/local-stack/
data/
  websites/
  databases/
  mail/
  dns/
  ftp/
  ssl/
```

## Current Install Mode
The installer currently uses a compose-backed local sandbox because it is the most reproducible way to keep all service configuration and lifecycle inside the repository while avoiding direct dependency on `/usr/local`, `/etc`, and `/var`.

Selected compose profiles are persisted in:
- `configs/install-config.json`

`--all` activates the full profile set:
- `core`
- `mail`
- `dns`
- `ftp`
- `security`
- `ops`

## Service Manager
The compose-backed manager lives at:
- `core/service-manager/service_manager.py`

Supported operations:
- `start_service()`
- `stop_service()`
- `restart_service()`
- `check_status()`
- `validate_config()`

CLI examples:

```bash
python core/service-manager/service_manager.py validate
python core/service-manager/service_manager.py start
python core/service-manager/service_manager.py status
python core/service-manager/service_manager.py stop redis
```

## Test Runner

```bash
python scripts/test_local_stack.py
```

Current smoke tests cover:
- selected web server HTTP endpoint
- selected database TCP reachability
- Redis TCP reachability
- Memcached TCP reachability
- phpMyAdmin HTTP endpoint

## Known Gaps
- Mail, DNS, FTP, and security containers are generated and staged, but not all are deeply validated yet.
- OpenLiteSpeed uses a container image path for the initial local sandbox instead of a source-compile flow.
- FirewallD and Fail2Ban inside containers are sandboxed and do not replace host firewall policy.

## Next Hardening Steps
1. Replace generated community-image dependencies with local Dockerfile builds where practical.
2. Add domain-driven mail and DNS integration tests.
3. Extend panel API routes to call the compose-backed service manager directly.
4. Add certbot issuance flow against a local ACME test endpoint or staging mode.
