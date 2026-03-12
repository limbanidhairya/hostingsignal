# STEP 4 — FULL HS-PANEL ARCHITECTURE

## Architecture Layers

```
┌─────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION (UI)                     │
│  HTML/CSS/JS served from /usr/local/hspanel/ui/ │
│  Admin UI (:2086) │ User UI (:2082)             │
├─────────────────────────────────────────────────┤
│  LAYER 2: API GATEWAY (hs-srvd)                 │
│  Perl HTTP daemon — JSON REST endpoints         │
│  Authentication, rate limiting, routing          │
├─────────────────────────────────────────────────┤
│  LAYER 3: BUSINESS LOGIC (HS::* Modules)        │
│  HS::Account  HS::Domain  HS::Mail  HS::DNS     │
│  HS::Database HS::SSL     HS::Backup HS::Cron   │
├─────────────────────────────────────────────────┤
│  LAYER 4: CONFIGURATION ENGINE                  │
│  Flat-file state in /var/hspanel/userdata/      │
│  Template system in /usr/local/hspanel/templates│
├─────────────────────────────────────────────────┤
│  LAYER 5: PRIVILEGE BOUNDARY                    │
│  C setuid wrappers in /usr/local/hspanel/bin/   │
│  Drops privileges before filesystem ops         │
├─────────────────────────────────────────────────┤
│  LAYER 6: SYSTEM AUTOMATION                     │
│  Bash scripts in /usr/local/hspanel/scripts/    │
│  rebuild_httpd.sh, rebuild_dns.sh, etc.         │
├─────────────────────────────────────────────────┤
│  LAYER 7: LINUX SERVICES                        │
│  Apache/Nginx, Postfix/Dovecot, Bind9, MariaDB  │
│  PHP-FPM, Pure-FTPd, OpenDKIM, SpamAssassin     │
└─────────────────────────────────────────────────┘
```

## Component Communication

### hs-srvd (Core Daemon)
- **Role**: Persistent Perl HTTP server listening on ports 2082 (user) and 2086 (admin)
- **Auth**: JWT tokens validated per-request; session cookies for browser UI
- **Routing**: URL path → Perl module method dispatch (e.g., `/api/account/create` → `HS::Account->create()`)
- **Concurrency**: Pre-fork model (configurable 4–16 workers)

### hs-taskd (Task Queue Daemon)
- **Role**: Background job executor watching `/var/hspanel/queue/pending/`
- **Jobs**: Backup generation, SSL provisioning, bulk DNS updates
- **Locking**: File-based exclusive locks prevent duplicate execution
- **Status**: Job results written to `/var/hspanel/queue/done/{job_id}.json`

### hs-logd (Log Aggregator)
- **Role**: Tail and parse service logs (Apache access, mail, DNS queries)
- **Output**: Structured JSON to `/usr/local/hspanel/logs/` for UI consumption

### Configuration Engine
- **State Storage**: `/var/hspanel/userdata/{username}/{domain}.yaml`
- **Flow**: Module writes state → rebuild script reads state → generates service config → reloads service
- **Rollback**: Previous configs archived to `.bak` before overwrite

### Plugin System
- **Location**: `/usr/local/hspanel/plugins/{plugin_name}/`
- **Manifest**: `plugin.json` defines hooks, routes, and UI menu entries
- **Hooks**: `pre_createacct`, `post_createacct`, `pre_killdomain`, etc.
- **Execution**: hs-srvd scans plugin directories at startup, registers hook callbacks

---

# STEP 5 — CORE FEATURES

| Feature | Perl Module | Key Operations |
|---------|-------------|----------------|
| Account Mgmt | `HS::Account` | create, suspend, terminate, change plan |
| Domain Mgmt | `HS::Domain` | add domain, add subdomain, park domain, redirect |
| Mail Server | `HS::Mail` | create mailbox, quota, forwarder, autoresponder |
| DNS Mgmt | `HS::DNS` | create zone, add/edit/delete records, templates |
| Database Mgmt | `HS::Database` | create DB, create user, grant privileges |
| File Manager | `HS::FileManager` | list, upload, download, extract, chmod, edit |
| SSL Mgmt | `HS::SSL` | install cert, AutoSSL (Let's Encrypt), renew |
| Backup System | `HS::Backup` | full, incremental, scheduled, restore, remote |
| Cron Scheduler | `HS::Cron` | list, add, edit, delete cron entries |
| Monitoring | `HS::Monitor` | CPU, RAM, disk, network, service status |

---

# STEP 6 — MAIL SERVER SYSTEM

## Architecture
```
                      Internet
                         │
              ┌──────────▼──────────┐
              │   Postfix (MTA)     │
              │   Port 25/587/465   │
              └──────────┬──────────┘
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
  ┌──────────────┐ ┌──────────┐ ┌───────────┐
  │ SpamAssassin │ │ OpenDKIM │ │ SPF Check │
  │ (spamc)      │ │ (milter) │ │ (policyd) │
  └──────┬───────┘ └────┬─────┘ └─────┬─────┘
         └──────────────┼─────────────┘
                        ↓
              ┌─────────────────────┐
              │   Dovecot LDA       │
              │   Local Delivery    │
              └─────────┬───────────┘
                        ↓
              /var/mail/vhosts/{domain}/{user}/
                        │
              ┌─────────▼───────────┐
              │   Dovecot           │
              │   IMAP: 993 (SSL)   │
              │   POP3: 995 (SSL)   │
              └─────────────────────┘
```

## Configuration Files Managed by HS-Panel

| File | Purpose |
|------|---------|
| `/etc/postfix/virtual_mailbox_domains` | List of hosted mail domains |
| `/etc/postfix/virtual_mailbox_maps` | Mailbox → filesystem mapping |
| `/etc/postfix/virtual_alias_maps` | Email forwarding rules |
| `/etc/dovecot/hspanel-users/` | Per-domain passwd files |
| `/etc/opendkim/KeyTable` | DKIM signing key mappings |
| `/etc/opendkim/SigningTable` | Domain → key selector map |
| `/etc/opendkim/keys/{domain}/` | DKIM private keys |

## HS::Mail Module Operations

```perl
# Create email account
HS::Mail->create_account({
    domain   => 'example.com',
    user     => 'info',
    password => $encrypted,
    quota    => '1024M'
});
# Writes to: /etc/dovecot/hspanel-users/example.com
# Updates:   /etc/postfix/virtual_mailbox_maps
# Reloads:   postfix, dovecot

# Create forwarder
HS::Mail->create_forwarder({
    source => 'sales@example.com',
    dest   => 'admin@example.com'
});
# Updates: /etc/postfix/virtual_alias_maps
```

---

# STEP 7 — DNS MANAGEMENT

## Bind9 Integration
```
/var/named/
├── example.com.db        ← Zone file
├── example2.com.db
└── ...

/etc/bind/named.conf.local   ← includes hspanel-zones.conf
/etc/bind/hspanel-zones.conf ← auto-generated zone declarations
```

## Zone File Template
```
$TTL 14400
@   IN  SOA  ns1.{hostname}. admin.{domain}. (
        {serial}    ; Serial (YYYYMMDDNN)
        3600        ; Refresh
        1800        ; Retry
        604800      ; Expire
        86400 )     ; Minimum TTL

    IN  NS   ns1.{hostname}.
    IN  NS   ns2.{hostname}.
    IN  A    {server_ip}
    IN  MX   10 mail.{domain}.

www IN  A    {server_ip}
mail IN A    {server_ip}
```

## HS::DNS Operations
- `create_zone($domain)` — Generate zone file, add to `hspanel-zones.conf`, `rndc reload`
- `add_record($domain, $type, $name, $value, $ttl)` — Parse zone, insert record, increment serial
- `delete_record($domain, $record_id)` — Remove line, increment serial, reload
- `apply_template($domain, $template_name)` — Load from `/usr/local/hspanel/templates/dns/`

---

# STEP 8 — FILE MANAGER

## Architecture
```
Browser (JS File Manager UI)
         │
    AJAX/Fetch API
         │
    hs-srvd /api/fileman/*
         │
    HS::FileManager (Perl)
         │
    wrap_fileop (C setuid binary)
         │
    setuid(target_user) → filesystem ops
         │
    /home/{username}/
```

## Security Model
1. `wrap_fileop.c` compiled with `setuid root`
2. Before any operation: validates user owns the target path
3. Calls `setuid(uid)` + `setgid(gid)` to drop to user privileges
4. Operations restricted to `/home/{username}/` — path traversal blocked via `realpath()` validation
5. File size limits enforced per-operation

## API Endpoints
| Endpoint | Method | Action |
|----------|--------|--------|
| `/api/fileman/list` | GET | List directory contents |
| `/api/fileman/upload` | POST | Upload file (multipart) |
| `/api/fileman/download` | GET | Download file |
| `/api/fileman/extract` | POST | Extract archive (zip/tar.gz) |
| `/api/fileman/edit` | GET/POST | Read/write file content |
| `/api/fileman/chmod` | POST | Change permissions |
| `/api/fileman/mkdir` | POST | Create directory |
| `/api/fileman/delete` | POST | Delete file/directory |
| `/api/fileman/rename` | POST | Rename/move file |
| `/api/fileman/copy` | POST | Copy file/directory |
