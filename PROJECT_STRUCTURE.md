# HS-Panel Project Structure

This document maps the canonical directory structure to the existing source locations.

## New Layout

```
hostingsignal/
  installer/
    install.sh               ← install.sh (root)
    services/
      build-scripts/         ← deployment/
  configs/
    panel.yml                ← config/panel.yml
    service-bundle.yml       ← config/service-bundle.yml
    docker-compose.yml       ← deployment/docker-compose.yml
  core/
    service-manager/         ← usr/local/hspanel/backend/service_manager/
  panel/
    frontend/                ← developer-panel/web/
    backend/                 ← usr/local/hspanel/backend/
  data/
    queue/                   ← var/hspanel/queue/
    users/                   ← var/hspanel/users/
    userdata/                ← var/hspanel/userdata/
  logs/                      ← usr/local/hspanel/logs/
  scripts/                   ← updates/, cli/
  tests/                     ← tests/ (this directory)
  reports/                   ← reports/ (generated test reports)
```

## Component Summary

| Component | Technology | Port | Status |
|-----------|-----------|------|--------|
| Panel Frontend | Next.js 14 | 3000 | ✓ Running |
| Panel Backend API | FastAPI + SQLite | 2083 | ✓ Running |
| Developer API | FastAPI + SQLite | 2087 | ✓ Running |
| PostgreSQL | postgres:16 | 5432 | ✓ Running |
| Redis | redis:7 | 6379 | ✓ Running |
| MariaDB (local) | mariadb:11 | 3309 | ✓ Running |
| phpMyAdmin | phpmyadmin | 8084 | ✓ Running |
| Apache (local) | httpd | 8081 | ✓ Running |
| PowerDNS | pdns-auth-49 | 8053/8081 | ✓ Running |
| License Server | FastAPI | 8443 | ✓ Running |
| RabbitMQ | rabbitmq:3 | 5672/15672 | ✓ Running |
