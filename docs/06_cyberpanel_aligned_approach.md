---
title: CyberPanel Aligned Approach
permalink: /06_cyberpanel_aligned_approach/
---

# 06 - CyberPanel-Aligned Build Approach

## Why the old approach failed

The previous installer mixed unrelated stack choices (Apache/BIND) while the panel goals require an OpenLiteSpeed-first stack with PowerDNS and service-level orchestration. It also copied files directly into system paths without a reliable local staging layer for required service artifacts.

## New approach (service-first)

HostingSignal now follows a CyberPanel-inspired model:

1. Install and manage hosting services first.
2. Keep panel UI as the control layer.
3. Add explicit service adapters around real daemons and package tools.
4. Use a local artifact root to stage/download open-source dependencies before install.

This keeps behavior predictable and makes install failures easier to isolate.

## Installer pipeline

`install.sh` now supports explicit modes:

- `stage`: download and cache artifacts to a local root.
- `install`: install required packages for the selected OS.
- `configure`: wire panel directories and local webapps.
- `all`: run all phases in order.

Default local bundle root: `./local/services`

## Required stack mapping

- Web server: OpenLiteSpeed (default) or LiteSpeed Enterprise (manual license path).
- Database: MariaDB or MySQL + phpMyAdmin.
- Cache: LSCache through OpenLiteSpeed stack.
- Email: Rainloop + Postfix + Dovecot.
- DNS: PowerDNS.
- Security: CSF, ModSecurity (OWASP CRS), ImunifyAV.
- File management: panel file manager + Pure-FTPd.
- PHP: multi-version packages (8.1/8.2/8.3 baseline).
- Other: Docker, Git, Let's Encrypt.

## CyberPanel reference usage

The installer stages a local clone of CyberPanel (`stable`) under:

- `./local/services/source/cyberpanel`

Purpose:

- Compare module boundaries and service management flow.
- Reuse architecture ideas (service orchestration, not UI replacement).
- Keep HostingSignal UI and user journey unchanged.

## Operations examples

```bash
# Full run (stage + install + configure)
sudo ./install.sh --mode all

# Use a custom local service root
sudo ./install.sh --mode all --local-root /opt/hs-services

# Download all artifacts first (offline prep)
sudo ./install.sh --mode stage --local-root /opt/hs-services

# Install only system packages from prepared bundle
sudo ./install.sh --mode install --db-engine mariadb

# Configure panel links after packages are ready
sudo ./install.sh --mode configure
```

## Notes

- Package names differ by distro and repository availability; installer logs unresolved packages and continues.
- LiteSpeed Enterprise is optional and requires your own license and binary deployment.
- This document describes the installation architecture and not UI changes.
