---
title: Universal Install Guide
description: One-command full-stack installation and OS-specific install paths.
permalink: /install/
---

# Universal Install Guide

Use this page for native production VPS install and optional local sandbox install.

## One Command (Full Stack)

Production master installer from GitHub (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh | sudo bash
```

Direct master script path:

```bash
curl -fsSL https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/installer/install.sh | sudo bash
```

From a local repository checkout (production stack):

```bash
sudo bash installer/install.sh --unattended
```

From a local repository checkout (optional Docker sandbox only):

```bash
python3 scripts/local_installer.py --mode all --all --non-interactive --web openlitespeed --db mariadb
```

Production installer command installs core services natively on the host OS:

- OpenLiteSpeed
- MariaDB
- PHP (multi-version)
- PowerDNS
- Postfix + Dovecot + Rainloop
- phpMyAdmin
- HS-Panel services via systemd

## Core-Only Fallback (Local Dev)

```bash
python3 scripts/local_installer.py --non-interactive --profile-set core --web openlitespeed --db mariadb
```

Use this when you want a lighter local stack.

## Profile Modes

- Full stack: `--mode all --all`
- Core only: `--profile-set core`
- Custom profiles: `--profiles core,mail,dns`

## OS Paths

### Linux (Ubuntu/Debian)

```bash
curl -fsSL https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh | sudo bash
```

### Windows (WSL2 Ubuntu 24.04)

First ensure WSL networking and package repositories are reachable, then:

```bash
sudo apt update && sudo apt install -y python3 python3-pip
curl -fsSL https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh | sudo bash
```

If you specifically want the optional local Docker sandbox mode:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
python3 scripts/local_installer.py --mode all --all --non-interactive --web openlitespeed --db mariadb
```

### Core-only quick run

```bash
python3 scripts/local_installer.py --non-interactive --profile-set core --web apache --db mariadb
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