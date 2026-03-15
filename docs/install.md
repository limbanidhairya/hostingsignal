---
title: Universal Install Guide
description: One-command full-stack installation and OS-specific install paths.
permalink: /install/
---

# Universal Install Guide

Use this page for the production-style local sandbox install flow.

## One Command (Full Stack)

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

This command:

- writes `configs/install-config.json`
- renders `runtime/local-stack/docker-compose.yml`
- prepares service workspaces under `services/`
- starts the full selected profile set

## Core-Only Fallback

```bash
bash ./install.sh --non-interactive --profile-set core --web openlitespeed --db mariadb
```

Use this when you want a lighter local stack.

## Profile Modes

- Full stack: `--mode all --all`
- Core only: `--profile-set core`
- Custom profiles: `--profiles core,mail,dns`

## OS Paths

### Linux (Ubuntu/Debian)

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

### Windows (WSL2 Ubuntu 24.04)

```bash
sudo apt update && sudo apt install -y python3 python3-pip docker-compose-plugin
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

### Core-only quick run

```bash
bash ./install.sh --non-interactive --profile-set core --web apache --db mariadb
```

## Verify After Install

```bash
python scripts/test_local_stack.py
python core/service-manager/service_manager.py status
```

## Related Pages

- [Admin Reference]({{ '/admin_reference/' | relative_url }})
- [Local Services Installer]({{ '/local_services_installer/' | relative_url }})
- [Release Scope]({{ '/release_scope_2026-03-15/' | relative_url }})