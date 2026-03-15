---
title: Queue Security Plugins Microservices
permalink: /05_queue_security_plugins_microservices/
---

# STEP 14 — TASK QUEUE SYSTEM

## Architecture
```
┌──────────┐     ┌──────────────────────┐     ┌──────────────┐
│ hs-srvd  │────→│ /var/hspanel/queue/  │←────│  hs-taskd    │
│ (writer) │     │    pending/          │     │  (executor)  │
└──────────┘     └──────────────────────┘     └──────┬───────┘
                                                      │
                                               ┌──────▼───────┐
                                               │ Execute job: │
                                               │ Bash/Perl    │
                                               └──────┬───────┘
                                                      │
                                              ┌───────▼────────┐
                                              │ done/ or fail/ │
                                              └────────────────┘
```

## Job File Format
```json
{
  "job_id": "a1b2c3d4-5678-90ab-cdef",
  "type": "create_account",
  "priority": 5,
  "submitted_by": "admin",
  "submitted_at": "2026-03-12T20:00:00Z",
  "params": {
    "username": "newuser",
    "domain": "example.com",
    "plan": "starter",
    "email": "admin@example.com"
  },
  "status": "pending"
}
```

## Job Types
| Type | Script/Module | Avg Duration |
|------|--------------|-------------|
| `create_account` | `HS::Account->create()` | 5-15s |
| `create_domain` | `HS::Domain->add()` | 3-8s |
| `create_email` | `HS::Mail->create_account()` | 2-5s |
| `create_database` | `HS::Database->create()` | 1-3s |
| `generate_ssl` | `ssl_renew.sh` | 15-60s |
| `run_backup` | `backup_account.sh` | 30s-30min |
| `rebuild_configs` | `rebuild_httpd.sh` | 5-15s |
| `dns_cluster_sync` | `HS::DNS->sync_cluster()` | 5-30s |

## hs-taskd Worker Logic (Perl)
```perl
#!/usr/bin/perl
# /usr/local/hspanel/daemon/hs-taskd.pl
use strict; use warnings;
use JSON; use File::Copy;

my $QUEUE_DIR = '/var/hspanel/queue';

while (1) {
    opendir(my $dh, "$QUEUE_DIR/pending") or die $!;
    my @jobs = sort grep { /\.json$/ } readdir($dh);
    closedir($dh);

    for my $jf (@jobs) {
        my $src  = "$QUEUE_DIR/pending/$jf";
        my $lock = "$QUEUE_DIR/running/$jf";
        next unless rename($src, $lock); # atomic lock

        my $job = decode_json(do { local(@ARGV,$/) = $lock; <> });
        $job->{status} = 'running';
        $job->{started_at} = scalar localtime;

        eval { execute_job($job) };
        if ($@) {
            $job->{status} = 'failed';
            $job->{error} = "$@";
            move($lock, "$QUEUE_DIR/failed/$jf");
        } else {
            $job->{status} = 'done';
            $job->{completed_at} = scalar localtime;
            move($lock, "$QUEUE_DIR/done/$jf");
        }
    }
    sleep 2;
}
```

---

# STEP 15 — SECURITY ARCHITECTURE

## Privilege Separation Model
```
┌──────────────────────┐
│  Browser (untrusted) │
└──────────┬───────────┘
           │ HTTPS
┌──────────▼───────────┐
│  hs-srvd (root)      │ ← Runs as root, but NEVER executes
│  Perl HTTP daemon     │   filesystem ops directly
└──────────┬───────────┘
           │ Internal call
┌──────────▼───────────┐
│  HS::* Modules        │ ← Business logic, validation
│  (no root ops here)   │
└──────────┬───────────┘
           │ Exec
┌──────────▼───────────┐
│  C Wrappers (setuid)  │ ← Only approved operations
│  Whitelist enforced   │   Drops to target user UID
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  System Operations    │
│  (as target user)     │
└──────────────────────┘
```

## Security Layers
1. **API Authentication**: JWT tokens with HMAC-SHA256, 1-hour expiry, refresh rotation
2. **Rate Limiting**: 100 req/min per IP for API, 5 login attempts per 15 min
3. **Input Validation**: All parameters sanitized; shell metacharacters stripped via whitelist regex
4. **Filesystem Jailing**: Users confined to `/home/{user}/` via `open_basedir`, `CageFS`, or `jailkit`
5. **SQL Injection Prevention**: Parameterized queries via DBI placeholders
6. **CSRF Protection**: Double-submit cookie pattern for all state-changing API calls
7. **Service Isolation**: Each PHP-FPM pool runs as the owning user (no shared pools)
8. **Firewall Integration**: `iptables`/`firewalld` rules managed via `/usr/local/hspanel/security/`
9. **Audit Logging**: All admin actions logged to `/usr/local/hspanel/logs/audit.log` with timestamps/IPs
10. **Brute Force Protection**: Fail2Ban jails for SSH, panel login, mail auth

## Firewall Default Rules
```
# Ports opened by HS-Panel installer
TCP 22    - SSH
TCP 25    - SMTP
TCP 53    - DNS
UDP 53    - DNS
TCP 80    - HTTP
TCP 443   - HTTPS
TCP 587   - SMTP Submission
TCP 993   - IMAPS
TCP 995   - POP3S
TCP 2082  - User Panel
TCP 2086  - Admin Panel
TCP 3306  - MySQL (localhost only)
TCP 21    - FTP (optional)
```

---

# STEP 16 — PLUGIN SDK

## Plugin Directory Structure
```
/usr/local/hspanel/plugins/my-plugin/
├── plugin.json       # Manifest
├── handler.pl        # Main Perl handler
├── ui/               # Optional UI assets
│   ├── page.html
│   └── style.css
└── scripts/          # Optional automation scripts
    └── setup.sh
```

## Plugin Manifest (`plugin.json`)
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "author": "Developer Name",
  "description": "A sample HS-Panel plugin",
  "min_panel_version": "2.0.0",
  "hooks": {
    "post_createacct": "handler.pl::on_account_created",
    "pre_killdomain": "handler.pl::before_domain_delete"
  },
  "routes": [
    {
      "path": "/api/plugin/my-plugin/status",
      "method": "GET",
      "handler": "handler.pl::api_status"
    }
  ],
  "ui_menu": [
    {
      "section": "admin",
      "label": "My Plugin",
      "icon": "puzzle",
      "page": "ui/page.html"
    }
  ],
  "permissions": ["read_accounts", "manage_dns"]
}
```

## Hook System
- **Available Hooks**: `pre_createacct`, `post_createacct`, `pre_killdomain`, `post_killdomain`, `pre_addmail`, `post_addmail`, `pre_backup`, `post_backup`, `pre_ssl_install`, `post_ssl_install`
- **Execution**: hs-srvd calls registered hooks synchronously (pre_) or asynchronously (post_)
- **Data**: Hook receives JSON payload with operation context

## Plugin Handler Example
```perl
# /usr/local/hspanel/plugins/my-plugin/handler.pl
package MyPlugin;
use strict; use warnings;
use JSON;

sub on_account_created {
    my ($context) = @_;
    my $username = $context->{username};
    my $domain   = $context->{domain};
    # Custom logic: send welcome email, notify billing, etc.
    system("curl -s -X POST https://billing.example.com/api/new_account -d '{\"user\":\"$username\"}'");
    return { status => 'ok' };
}

sub api_status {
    my ($req) = @_;
    return { status => 'active', version => '1.0.0' };
}

1;
```

---

# STEP 17 — MICROSERVICE UPGRADE PATH

## Current: Monolithic Architecture
```
┌─────────────────────────────────┐
│        Single Server            │
│                                 │
│  hs-srvd ← All logic here      │
│  Apache, Bind9, Postfix, MySQL  │
│  All services on one machine    │
└─────────────────────────────────┘
```

## Future: Control Plane + Data Plane
```
┌─────────────────────────────────────────────────────────┐
│                  CONTROL PLANE (K8s Cluster)             │
│                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │
│  │ User       │ │ Billing    │ │ Central            │  │
│  │ Service    │ │ Service    │ │ Database (Postgres) │  │
│  │ (auth/SSO) │ │ (Stripe)   │ │                    │  │
│  └─────┬──────┘ └─────┬──────┘ └────────┬───────────┘  │
│        │              │                  │              │
│  ┌─────▼──────┐ ┌─────▼──────┐ ┌────────▼───────────┐  │
│  │ DNS        │ │ Mail       │ │ Monitoring         │  │
│  │ Service    │ │ Service    │ │ Service            │  │
│  │ (PowerDNS) │ │ (routing)  │ │ (Prometheus)       │  │
│  └─────┬──────┘ └─────┬──────┘ └────────┬───────────┘  │
│        │              │                  │              │
│        └──────────────┼──────────────────┘              │
│                       │ gRPC/REST API                   │
└───────────────────────┼─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼─────┐  ┌──────▼──────┐  ┌─────▼───────┐
│ Host Node 1 │  │ Host Node 2 │  │ Host Node N │
│             │  │             │  │             │
│ hs-agent    │  │ hs-agent    │  │ hs-agent    │
│ Apache      │  │ Apache      │  │ Apache      │
│ PHP-FPM     │  │ PHP-FPM     │  │ PHP-FPM     │
│ Postfix     │  │ Postfix     │  │ Postfix     │
│ Dovecot     │  │ Dovecot     │  │ Dovecot     │
│ MariaDB     │  │ MariaDB     │  │ MariaDB     │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Microservice Communication
| Service | Protocol | Responsibility |
|---------|----------|---------------|
| User Service | REST/gRPC | Authentication, SSO, user profiles |
| DNS Service | REST | Zone management via PowerDNS API |
| Mail Service | REST | Mail routing, mailbox provisioning |
| Database Service | REST | MySQL/Postgres grant management |
| Monitoring Service | gRPC + Prometheus | Metrics collection, alerting |
| Billing Service | REST | License validation, usage metering |

## hs-agent (Data Plane Agent)
- Lightweight Perl/Go agent running on each host node
- Listens on internal network only (not internet-facing)
- Receives commands: create user, write vhost, restart service
- Reports health metrics back to Control Plane
- Stateless — all state lives in Control Plane database
- Nodes are disposable and replaceable
