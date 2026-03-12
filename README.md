<p align="center">
  <img src="https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/frontend/public/logo.png" alt="HostingSignal Logo" width="200" onerror="this.src='https://via.placeholder.com/200?text=HostingSignal'"/>
</p>

<h1 align="center">HostingSignal Panel</h1>

<p align="center">
  <strong>Next-Generation, Production-Ready Web Hosting Control Panel</strong>
</p>

<p align="center">
  <img alt="Backend FastAPI" src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi">
  <img alt="Frontend Next.js" src="https://img.shields.io/badge/Frontend-Next.js-black?style=for-the-badge&logo=next.js">
  <img alt="License Server" src="https://img.shields.io/badge/License-JWT%20Secured-blue?style=for-the-badge">
  <img alt="CLI" src="https://img.shields.io/badge/CLI-hsctl-orange?style=for-the-badge">
</p>

---

**HostingSignal Panel** is a modern, scalable hosting control panel built from the ground up. Inspired by CyberPanel but redesigned with a cleaner architecture, it manages websites, domains, DNS, databases, email, SSL, backups, security, and monitoring through a beautiful Cloudflare-style dark UI.

## 🏗️ Architecture

```
hostingsignal/
├── license-server/          # Standalone license validation server (FastAPI + PostgreSQL)
├── backend/                 # Panel backend API (FastAPI + SQLAlchemy)
│   └── app/
│       ├── api/             # REST API routes (13 modules)
│       ├── core/            # Config, database, security, Redis, RabbitMQ
│       ├── daemon/          # Background monitor & scheduler
│       ├── models/          # Database models
│       └── services/        # Service managers (12 modules)
├── frontend/                # Next.js + React (Cloudflare-style UI)
│   └── src/
│       ├── app/(panel)/     # Panel pages (Dashboard, Websites, DNS, etc.)
│       └── components/      # Reusable UI components
├── cli/                     # hsctl CLI tool (Python Click)
├── systemd/                 # Service unit files (4 services)
├── installer/               # OS-specific setup scripts
├── deployment/              # Docker Compose, Kubernetes, CI/CD
├── config/                  # Default configuration templates
├── updates/                 # Update system
└── install.sh               # One-command installer
```

## 🚀 Quick Install

```bash
sudo ./install.sh --mode all
```

### Service-First Install Flow (CyberPanel-aligned)

```bash
# 1) Download/stage all open-source service artifacts locally
sudo ./install.sh --mode stage --local-root ./local/services

# 2) Install system packages for selected stack
sudo ./install.sh --mode install --db-engine mariadb --web-stack openlitespeed

# 3) Wire panel paths and staged webapps
sudo ./install.sh --mode configure --local-root ./local/services
```

Reference docs:
- `docs/06_cyberpanel_aligned_approach.md`
- `config/service-bundle.yml`

### Supported Operating Systems

| OS | Version | Status |
|---|---|---|
| Ubuntu | 22.04 LTS | ✅ Supported |
| Ubuntu | 24.04 LTS | ✅ Supported |
| Debian | 12 | ✅ Supported |
| AlmaLinux | 9 | ✅ Supported |

### System Requirements

- **RAM**: 1GB minimum (2GB+ recommended)
- **CPU**: 1 core minimum
- **Storage**: 20GB minimum
- **User**: Root access required

## ✨ Features

### Website Management
- Create/delete websites and subdomains
- OpenLiteSpeed integration (default) with multi-PHP management
- SSL management (Let's Encrypt auto-issue)
- Per-site disk usage tracking

### DNS Management
- Zone editor with full record support (A, AAAA, CNAME, MX, TXT, NS, SRV, CAA)
- PowerDNS-backed management (lightweight and fast)
- Nameserver management

### Database Management
- MySQL/MariaDB database CRUD
- User management with granular privileges
- phpMyAdmin integration

### Email Hosting
- Mail domain management
- Email account CRUD with quotas
- Rainloop Webmail integration
- Postfix + Dovecot service integration
- DKIM/SPF support

### Backup System
- Manual & scheduled backups
- Full, incremental, files-only, database-only types
- Remote backup support (S3, SFTP)
- Backup restoration

### Security
- ConfigServer Firewall (CSF)
- ModSecurity (WAF) with OWASP CRS
- ImunifyAV malware scanning
- SSL auto-renewal
- Login protection & rate limiting

### File and DevOps Tools
- File Manager and Pure-FTPd integration
- Docker Manager and Git Manager modules

### Monitoring
- Real-time CPU, RAM, disk, network stats
- WebSocket live data streaming
- Service health status
- Process monitor
- Historical metrics with charts

### License System
- JWT-based license validation
- Hardware fingerprint binding (CPU ID, disk UUID, MAC, machine ID)
- IP/domain binding
- Tiered licensing (Starter → Enterprise)

## 💻 CLI Tool (hsctl)

```bash
hsctl status          # Show service statuses
hsctl start           # Start all services
hsctl stop            # Stop all services
hsctl restart         # Restart all services
hsctl update          # Update panel
hsctl logs            # View service logs
hsctl license --info  # Show license info
hsctl create-site example.com --ssl
hsctl delete-site example.com
hsctl backup --type full
hsctl restore <backup_id>
```

## 🐳 Docker Deployment

```bash
cd deployment
docker compose up -d
```

Services: PostgreSQL, Redis, RabbitMQ, License Server, Backend API, Frontend

## ☸️ Kubernetes Deployment

```bash
kubectl apply -f deployment/k8s-deployment.yml
```

## 🔧 Tech Stack

| Component | Technology |
|---|---|
| Backend API | Python FastAPI |
| Frontend | Next.js 14 + React |
| UI | Custom CSS (Cloudflare-inspired dark theme) |
| Database | PostgreSQL / SQLite |
| Cache | Redis |
| Queue | RabbitMQ |
| Web Server | OpenLiteSpeed |
| CLI | Python Click |
| License | JWT + Hardware Fingerprint |

## 🛠️ Development Mode

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📋 Systemd Services

| Service | Description |
|---|---|
| `hostingsignal-api` | FastAPI backend (port 8080) |
| `hostingsignal-web` | Next.js frontend (port 3000) |
| `hostingsignal-daemon` | Background task scheduler |
| `hostingsignal-monitor` | System monitoring daemon |

## 📜 License Server API

| Endpoint | Method | Description |
|---|---|---|
| `/license/create` | POST | Create new license |
| `/license/activate` | POST | Activate on server |
| `/license/validate` | POST | Validate license |
| `/license/revoke` | POST | Revoke license |
| `/license/info` | GET | License details |
| `/license/status` | GET | Quick status check |

---

<p align="center">
  Built with ❤️ by the <a href="https://github.com/limbanidhairya">HostingSignal Team</a>
</p>
