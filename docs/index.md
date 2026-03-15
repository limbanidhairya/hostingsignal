---
title: HostingSignal Docs
description: Architecture, operations, installation, and release documentation.
permalink: /
---

<section class="hero">
	<div class="hero__copy">
		<span class="eyebrow">HostingSignal Documentation</span>
		<h1>Operational docs, release notes, and admin reference in one place.</h1>
		<p class="lead">Use this site as the central reference for platform architecture, install flows, release readiness, and runtime operations.</p>
		<div class="hero__actions">
			<a class="button button--primary" href="{{ '/install/' | relative_url }}">Start Install Guide</a>
			<a class="button button--ghost" href="{{ '/admin_reference/' | relative_url }}">Open Admin Reference</a>
			<a class="button button--ghost" href="{{ '/release_scope_2026-03-15/' | relative_url }}">View Release Scope</a>
		</div>
	</div>
	<div class="hero__brand">
		<img src="https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/developer-panel/web/public/branding/hostingsignal-logo.png" alt="HostingSignal Logo" width="180" />
	</div>
</section>

Welcome to the HostingSignal documentation hub.

## Universal Install Command

One command — no clone needed, runs directly from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh | bash
```

Local checkout variant:

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

Need step-by-step guidance? Open [Universal Install Guide]({{ '/install/' | relative_url }}).

## Quick Links

<div class="card-grid">
	<a class="card" href="{{ '/install/' | relative_url }}">
		<strong>Install Guide</strong>
		<span>Universal one-command install plus core-only and OS-specific paths.</span>
	</a>
	<a class="card" href="{{ '/admin_reference/' | relative_url }}">
		<strong>Admin Reference</strong>
		<span>Install commands, ports, domain notes, and operational checks.</span>
	</a>
	<a class="card" href="{{ '/release_scope_2026-03-15/' | relative_url }}">
		<strong>Release Scope</strong>
		<span>Current release snapshot, branch scope, and merge boundaries.</span>
	</a>
	<a class="card" href="{{ '/merge_checklist_2026-03-15/' | relative_url }}">
		<strong>Merge Checklist</strong>
		<span>What to verify before promoting release work.</span>
	</a>
	<a class="card" href="{{ '/local_services_installer/' | relative_url }}">
		<strong>Installer Guide</strong>
		<span>Local sandbox install flow and supported execution paths.</span>
	</a>
</div>

## What This Site Covers

- platform architecture and service map
- installer and deployment flows
- release operations and handoff material
- admin-oriented runtime and docs references

## Start Here

<div class="doc-list">
	<a href="{{ '/01_service_map/' | relative_url }}">Service Map</a>
	<a href="{{ '/02_architecture_and_subsystems/' | relative_url }}">Architecture and Subsystems</a>
	<a href="{{ '/03_webserver_automation_installer/' | relative_url }}">Webserver Automation Installer</a>
	<a href="{{ '/04_installer_script/' | relative_url }}">Installer Script</a>
	<a href="{{ '/05_queue_security_plugins_microservices/' | relative_url }}">Queue Security Plugins Microservices</a>
	<a href="{{ '/06_cyberpanel_aligned_approach/' | relative_url }}">CyberPanel Aligned Approach</a>
	<a href="{{ '/hspanel_architecture/' | relative_url }}">HS Panel Architecture</a>
</div>

## Release Notes and Operations

<div class="doc-list">
	<a href="{{ '/admin_reference/' | relative_url }}">Admin Reference</a>
	<a href="{{ '/release_scope_2026-03-15/' | relative_url }}">Release Scope - 2026-03-15</a>
	<a href="{{ '/merge_checklist_2026-03-15/' | relative_url }}">Merge Checklist - 2026-03-15</a>
	<a href="{{ '/build_status_iteration_2026-03-15/' | relative_url }}">Build Status - 2026-03-15</a>
	<a href="{{ '/handoff_2026-03-15/' | relative_url }}">Handoff - 2026-03-15</a>
</div>

## Install Quick Start

Universal one-command install for the current repo-local sandbox:

```bash
bash ./install.sh --mode all --all --non-interactive --web openlitespeed --db mariadb
```

Core-only fallback:

```bash
bash ./install.sh --non-interactive --profile-set core --web openlitespeed --db mariadb
```

Full install runbook page:

- [Universal Install Guide]({{ '/install/' | relative_url }})

Supported paths:

- Ubuntu 22.04 / 24.04
- Debian 12
- Windows 10 / 11 via WSL2 Ubuntu 24.04
- AlmaLinux 8 / 9 deployment target
- Rocky Linux 8 / 9 deployment target

## GitHub Pages Status

GitHub Pages docs are live.

- Live docs domain: `https://docs.hostingsignal.in/`
- Workflow file: `.github/workflows/docs-pages.yml`
- Source directory: `docs/`

If content looks stale, hard refresh and check the latest `Docs Pages` run in GitHub Actions.


