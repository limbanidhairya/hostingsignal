---
title: Webserver Automation Installer
permalink: /03_webserver_automation_installer/
---

# STEP 9 — WEB SERVER MANAGEMENT

## Multi-Engine Support

```
hs-srvd → HS::Web → detect_engine()
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
    ┌─────────┐    ┌──────────┐    ┌───────────┐
    │ Apache  │    │  Nginx   │    │OpenLiteSpd│
    │ httpd   │    │  nginx   │    │  lsws     │
    └────┬────┘    └────┬─────┘    └─────┬─────┘
         │              │                │
    Template:       Template:        Template:
    vhost.apache    vhost.nginx      vhost.ols
```

## Virtual Host Generation Flow
1. User adds domain via UI → `HS::Domain->add($domain)`
2. State written: `/var/hspanel/userdata/{user}/{domain}.yaml`
3. Rebuild triggered: `rebuild_httpd.sh`
4. Script reads all userdata, generates vhost configs from templates
5. Config test: `apachectl configtest` / `nginx -t`
6. If pass → `systemctl reload`; If fail → rollback `.bak`, alert admin

## PHP-FPM Pool Management
```
# Per-user pool: /etc/php/8.2/fpm/pool.d/{username}.conf
[{username}]
user = {username}
group = {username}
listen = /run/php/php8.2-fpm-{username}.sock
listen.owner = www-data
listen.group = www-data
pm = ondemand
pm.max_children = 5
pm.process_idle_timeout = 10s
php_admin_value[open_basedir] = /home/{username}/:/tmp/
```

---

# STEP 10 — LINUX SERVICE AUTOMATION

## Service Abstraction Layer

```perl
# /usr/local/hspanel/perl/HS/System.pm
package HS::System;

sub restart_service {
    my ($self, $service) = @_;
    my $result = $self->_exec("systemctl restart $service 2>&1");
    return { status => ($? == 0 ? 'ok' : 'error'), output => $result };
}

sub config_test {
    my ($self, $engine) = @_;
    my %tests = (
        apache => 'apachectl configtest 2>&1',
        nginx  => 'nginx -t 2>&1',
        named  => 'named-checkconf 2>&1',
        postfix => 'postfix check 2>&1',
    );
    return $self->_exec($tests{$engine});
}
```

## Automation Script Inventory

| Script | Purpose |
|--------|---------|
| `rebuild_httpd.sh` | Regenerate all Apache/Nginx vhosts from userdata |
| `rebuild_dns.sh` | Regenerate Bind zone files, reload named |
| `rebuild_mail.sh` | Regenerate Postfix virtual maps, Dovecot passwd |
| `rebuild_ftp.sh` | Regenerate Pure-FTPd virtual users |
| `restart_services.sh` | Graceful restart of all managed services |
| `backup_account.sh` | Full tarball backup of a single account |
| `ssl_renew.sh` | Certbot/acme.sh renewal wrapper |
| `quota_sync.sh` | Sync disk quotas from userdata to system |
| `ip_block.sh` | Add/remove firewall rules |
| `cleanup_tmp.sh` | Purge temp files older than 7 days |

---

# STEP 11 — UNIVERSAL INSTALLER DESIGN

## Supported Matrix

| OS | Versions | Package Mgr | Web Server Pkg | Init |
|----|----------|-------------|----------------|------|
| Ubuntu | 22.04, 24.04 | apt | apache2 | systemd |
| Debian | 12 | apt | apache2 | systemd |
| AlmaLinux | 8, 9 | dnf | httpd | systemd |
| Rocky Linux | 8, 9 | dnf | httpd | systemd |

## Installer Phases

```
Phase 1: Pre-flight Checks
  ├── Verify root access
  ├── Detect OS via /etc/os-release
  ├── Check minimum RAM (1GB)
  ├── Check minimum disk (20GB)
  ├── Verify no conflicting panel installed
  └── Check network connectivity

Phase 2: Dependency Installation
  ├── Update package manager cache
  ├── Install build tools (gcc, make, autoconf)
  ├── Install Perl + CPAN modules
  ├── Install web server (Apache default)
  ├── Install Bind9/Named
  ├── Install Postfix + Dovecot
  ├── Install MariaDB
  ├── Install Pure-FTPd
  ├── Install PHP-FPM (8.1, 8.2, 8.3)
  ├── Install certbot
  ├── Install Redis (for queue)
  └── Install OpenDKIM, SpamAssassin

Phase 3: Compilation
  ├── Compile C wrappers (wrap_sysop, wrap_fileop)
  ├── Set setuid permissions (chmod 4755)
  └── Compile any custom utilities

Phase 4: Configuration
  ├── Create /usr/local/hspanel/ directory tree
  ├── Create /var/hspanel/ state directories
  ├── Generate SSL cert for panel (self-signed)
  ├── Configure Postfix for virtual hosting
  ├── Configure Dovecot with hspanel auth
  ├── Configure Bind9 with hspanel zones
  ├── Configure Apache with default vhost
  ├── Set up PHP-FPM default pool
  ├── Initialize MariaDB root password
  └── Configure firewall (open 80,443,2082,2086,25,587,993,995,53)

Phase 5: Initialize HS-Panel
  ├── Create admin user in /var/hspanel/users/
  ├── Generate JWT secret
  ├── Install systemd units (hspanel, hspanel-taskd)
  ├── Enable and start daemons
  └── Print access URL and credentials
```

---

# STEP 12 — PRODUCTION FOLDER STRUCTURE

```
/usr/local/hspanel/
├── api/                    # REST API route definitions
│   ├── routes.pl           # Master router
│   ├── account.pl          # /api/account/* handlers
│   ├── domain.pl           # /api/domain/* handlers
│   ├── mail.pl             # /api/mail/* handlers
│   ├── dns.pl              # /api/dns/* handlers
│   ├── database.pl         # /api/database/* handlers
│   ├── fileman.pl          # /api/fileman/* handlers
│   ├── ssl.pl              # /api/ssl/* handlers
│   ├── backup.pl           # /api/backup/* handlers
│   ├── cron.pl             # /api/cron/* handlers
│   └── monitor.pl          # /api/monitor/* handlers
│
├── bin/                    # Compiled C binaries (setuid)
│   ├── wrap_sysop          # System operations wrapper
│   ├── wrap_fileop         # File operations wrapper
│   ├── wrap_mailop         # Mail operations wrapper
│   └── wrap_dbop           # Database operations wrapper
│
├── config/                 # Panel internal configuration
│   ├── hspanel.conf        # Main config (ports, paths, features)
│   ├── license.key         # License file
│   └── ssl/                # Panel's own SSL cert/key
│       ├── panel.crt
│       └── panel.key
│
├── daemon/                 # Core Perl daemons
│   ├── hs-srvd.pl          # HTTP API server
│   ├── hs-taskd.pl         # Background task executor
│   └── hs-logd.pl          # Log aggregator
│
├── logs/                   # Panel logs
│   ├── access.log          # API access log
│   ├── error.log           # Error log
│   └── task.log            # Task queue execution log
│
├── perl/                   # Perl library modules
│   └── HS/
│       ├── Core.pm         # Core utilities, config loader
│       ├── Auth.pm         # JWT, session management
│       ├── Account.pm      # Account CRUD
│       ├── Domain.pm       # Domain management
│       ├── Mail.pm         # Email account management
│       ├── DNS.pm          # Zone file management
│       ├── Database.pm     # MySQL/PostgreSQL management
│       ├── FileManager.pm  # File operations
│       ├── SSL.pm          # Certificate management
│       ├── Backup.pm       # Backup/restore
│       ├── Cron.pm         # Cron job management
│       ├── Monitor.pm      # System metrics
│       ├── System.pm       # Service control (systemctl)
│       └── Plugin.pm       # Plugin loader and hooks
│
├── plugins/                # Third-party plugin directory
│   └── example-plugin/
│       ├── plugin.json     # Manifest (hooks, routes, UI)
│       └── handler.pl      # Plugin logic
│
├── scripts/                # Bash automation scripts
│   ├── rebuild_httpd.sh
│   ├── rebuild_dns.sh
│   ├── rebuild_mail.sh
│   ├── rebuild_ftp.sh
│   ├── backup_account.sh
│   ├── ssl_renew.sh
│   └── quota_sync.sh
│
├── security/               # Security utilities
│   ├── firewall.sh         # iptables/firewalld wrapper
│   └── jail.sh             # Jailkit setup
│
├── src/                    # C source files
│   ├── wrap_sysop.c
│   ├── wrap_fileop.c
│   ├── wrap_mailop.c
│   ├── wrap_dbop.c
│   └── Makefile
│
├── templates/              # Service config templates
│   ├── apache/
│   │   ├── vhost.tmpl
│   │   ├── vhost-ssl.tmpl
│   │   └── php-fpm-pool.tmpl
│   ├── nginx/
│   │   ├── server.tmpl
│   │   └── server-ssl.tmpl
│   ├── dns/
│   │   ├── zone.tmpl
│   │   └── standard.tmpl
│   ├── mail/
│   │   ├── dovecot-user.tmpl
│   │   └── dkim.tmpl
│   └── ui/
│       ├── guest-page.html
│       └── error-pages/
│
├── cache/                  # Runtime cache
│   ├── sessions/           # JWT session cache
│   └── templates/          # Pre-compiled templates
│
└── ui/                     # Frontend static assets
    ├── admin/              # Admin panel (HTML/CSS/JS)
    │   ├── index.html
    │   ├── css/
    │   ├── js/
    │   └── img/
    ├── user/               # User panel (HTML/CSS/JS)
    │   ├── index.html
    │   ├── css/
    │   ├── js/
    │   └── img/
    └── guest/              # Default server page
        └── index.html

/var/hspanel/
├── userdata/               # Per-user configuration state
│   └── {username}/
│       ├── main.yaml       # Account metadata
│       ├── {domain}.yaml   # Domain configuration
│       └── ssl/            # User SSL certs
├── users/                  # User registry
│   └── {username}.json     # UID, plan, quotas, features
├── queue/                  # Task queue
│   ├── pending/            # Pending jobs
│   ├── running/            # Currently executing
│   ├── done/               # Completed jobs
│   └── failed/             # Failed jobs
└── backups/                # Backup storage
    └── {username}/
        └── {timestamp}.tar.gz
```
