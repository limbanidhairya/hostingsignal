<p align="center">
	<img src="https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/developer-panel/web/public/branding/hostingsignal-logo.png" alt="HostingSignal Logo" width="170" />
</p>

# HostingSignal Documentation

Welcome to the HostingSignal documentation hub.

## Quick Links

- Live docs domain: `https://docs.hostingsignal.in/`
- Admin reference: [admin_reference.md](admin_reference.md)
- Release scope: [release_scope_2026-03-15.md](release_scope_2026-03-15.md)
- Merge checklist: [merge_checklist_2026-03-15.md](merge_checklist_2026-03-15.md)

## What This Site Covers

- platform architecture and service map
- installer and deployment flows
- release operations and handoff material
- admin-oriented runtime and docs references

## Start Here

- [Service Map](01_service_map.md)
- [Architecture and Subsystems](02_architecture_and_subsystems.md)
- [Webserver Automation Installer](03_webserver_automation_installer.md)
- [Installer Script](04_installer_script.md)
- [Queue Security Plugins Microservices](05_queue_security_plugins_microservices.md)
- [CyberPanel Aligned Approach](06_cyberpanel_aligned_approach.md)
- [HS Panel Architecture](hspanel_architecture.md)

## Release Notes and Operations

- [Admin Reference](admin_reference.md)
- [Release Scope - 2026-03-15](release_scope_2026-03-15.md)
- [Merge Checklist - 2026-03-15](merge_checklist_2026-03-15.md)
- [Build Status - 2026-03-15](build_status_iteration_2026-03-15.md)
- [Handoff - 2026-03-15](handoff_2026-03-15.md)

## Install Quick Start

Master install command for the current repo-local sandbox:

```bash
bash ./install.sh --non-interactive --web openlitespeed --db mariadb
```

Supported paths:

- Ubuntu 22.04 / 24.04
- Debian 12
- Windows 10 / 11 via WSL2 Ubuntu 24.04
- AlmaLinux 8 / 9 deployment target
- Rocky Linux 8 / 9 deployment target

## GitHub Pages Status

GitHub Pages deployment workflow is configured.

- Workflow file: `.github/workflows/docs-pages.yml`
- Source directory: `docs/`
- Custom domain: `https://docs.hostingsignal.in/`

Custom domain is now configured in-repo. Finish by confirming the domain in GitHub Pages settings and enabling HTTPS after validation.


