---
title: Admin Reference
description: Operational reference for install, platform ports, Pages domain, and release tracking.
permalink: /admin_reference/
---

<section class="hero hero--compact">
  <div class="hero__copy">
    <span class="eyebrow">Admin Reference</span>
    <h1>Runtime, install, and release controls for HostingSignal administrators.</h1>
    <p class="lead">This page collects the commands and references you are most likely to need when operating the current HostingSignal release.</p>
  </div>
  <div class="hero__brand">
    <img src="https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/developer-panel/web/public/branding/hostingsignal-logo.png" alt="HostingSignal Logo" width="160" />
  </div>
</section>

# HostingSignal Admin Reference

This page is the admin-facing reference for installs, release status, service ports, and documentation entrypoints.

## Primary Admin URLs

- GitHub Pages docs root: `https://docs.hostingsignal.in/`
- Admin reference page: `https://docs.hostingsignal.in/admin_reference/`
- Local partner panel: `http://localhost:3000/`
- Local dev API docs: `http://localhost:2087/api/docs`

## Master Install Command

Use this command to generate, configure, and start the full HostingSignal local stack in one run:

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

Core-only fallback:

```bash
bash ./install.sh --non-interactive --profile-set core --web openlitespeed --db mariadb
```

Detailed install runbook:

- [Universal Install Guide]({{ '/install/' | relative_url }})

Prerequisites:

- `python3`
- `docker compose`
- Git checkout of this repository

## Supported OS Matrix

| Platform | Support level | Notes |
|---|---|---|
| Ubuntu 22.04 / 24.04 | Supported | Preferred native Linux path |
| Debian 12 | Supported | Native Linux path |
| AlmaLinux 8 / 9 | Deployment target | Use Linux deployment docs and validate service packages |
| Rocky Linux 8 / 9 | Deployment target | Use Linux deployment docs and validate service packages |
| Windows 10 / 11 | Supported through WSL2 | Use Ubuntu 24.04 in WSL and Docker Desktop integration |

## Windows via WSL2

Run inside Ubuntu WSL:

```bash
sudo apt update && sudo apt install -y python3 python3-pip docker-compose-plugin
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

If Docker is provided by Docker Desktop, enable WSL integration for the target distro first.

## Linux Native

Run on supported Linux hosts:

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

## Core Runtime Ports

| Service | Port |
|---|---:|
| Partner panel | `3000` |
| Dev API | `2087` |
| Core daemon | `2086` |
| Core API | `2083` |

## Release Snapshot

- Current tag: `v1.0.0`
- Release branch: `release/2026-03-15-rc1`
- Latest release docs: `release_scope_2026-03-15.md`
- Latest handoff: `handoff_2026-03-15.md`

## GitHub Pages Publishing Notes

- Workflow file: `.github/workflows/docs-pages.yml`
- Source folder: `docs/`
- Custom domain: `docs.hostingsignal.in`
- Domain file: `docs/CNAME`

Final GitHub-side check:

1. Open repository `Settings -> Pages`
2. Ensure source is `GitHub Actions`
3. Ensure the deployed site shows custom domain `docs.hostingsignal.in`
4. Enable HTTPS after GitHub validates the DNS

## Recommended Admin Reading Order

1. `index.md`
2. `release_scope_2026-03-15.md`
3. `merge_checklist_2026-03-15.md`
4. `handoff_2026-03-15.md`
