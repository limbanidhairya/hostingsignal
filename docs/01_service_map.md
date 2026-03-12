# STEP 1 — HS-PANEL INTERNAL SERVICE MAP

## Master Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HS-PANEL CONTROL PLANE                       │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Admin UI │  │ User UI  │  │ Guest UI │  │ API Clients/CLI  │   │
│  │ :2086    │  │ :2082    │  │ :80/443  │  │ hsctl            │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                  │             │
│       └──────────────┴──────────────┴──────────────────┘             │
│                              │                                      │
│                    ┌─────────▼──────────┐                           │
│                    │   hs-srvd (Perl)   │  ← HTTP Daemon            │
│                    │   Ports 2082/2086  │                           │
│                    └─────────┬──────────┘                           │
│                              │                                      │
│              ┌───────────────┼───────────────┐                      │
│              │               │               │                      │
│    ┌─────────▼─────┐ ┌──────▼──────┐ ┌─────▼──────────┐           │
│    │ HS::* Modules │ │ Task Queue  │ │ Config Engine  │           │
│    │ (Perl Libs)   │ │ hs-taskd    │ │ /var/hspanel/  │           │
│    └───────┬───────┘ └──────┬──────┘ └──────┬─────────┘           │
│            │                │                │                      │
│    ┌───────▼────────────────▼────────────────▼──────────┐          │
│    │          C Wrappers (setuid binaries)               │          │
│    │          /usr/local/hspanel/bin/                     │          │
│    └───────┬────────────────┬────────────────┬──────────┘          │
└────────────┼────────────────┼────────────────┼──────────────────────┘
             │                │                │
┌────────────▼────────────────▼────────────────▼──────────────────────┐
│                     LINUX SYSTEM SERVICES                           │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │  Apache  │ │ Postfix  │ │  Bind9   │ │ MariaDB  │ │  Pure-  │ │
│  │  Nginx   │ │ Dovecot  │ │ PowerDNS │ │ Postgres │ │  FTPd   │ │
│  │  OLS     │ │ SpamAsn  │ │          │ │          │ │         │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ PHP-FPM  │ │ OpenDKIM │ │ certbot  │ │ iptables │             │
│  │ pools    │ │          │ │ acme.sh  │ │ firewalld│             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Linux Filesystem                          │   │
│  │  /home/users/   /var/mail/   /var/named/   /etc/            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow Maps

### Web Request Flow
```
Browser → DNS Resolver → Bind9/PowerDNS → IP Resolution
                                              ↓
Browser ──HTTP/HTTPS──→ Apache/Nginx/OLS (:80/:443)
                              ↓
                     Virtual Host Matching
                              ↓
                     PHP-FPM (unix socket)
                              ↓
                     /home/user/public_html/
                              ↓
                     MariaDB (if dynamic)
                              ↓
                     Response → Browser
```

### Email Delivery Flow
```
Sender MTA ──SMTP:25──→ Postfix (MTA)
                            ↓
                     SpamAssassin (spamc)
                            ↓
                     OpenDKIM (verify/sign)
                            ↓
                     Virtual Transport Map
                            ↓
                     Dovecot LDA → /var/mail/vhosts/domain/user/
                            ↓
User Client ──IMAP:993──→ Dovecot → Mailbox → Response
User Client ──POP3:995──→ Dovecot → Mailbox → Response
```

### DNS Resolution Flow
```
Client Query → Recursive Resolver → Root NS
                                       ↓
                              TLD NS (.com)
                                       ↓
                              Authoritative NS (Bind9)
                                       ↓
                     Zone File: /var/named/domain.com.db
                                       ↓
                              A Record → IP Address
                                       ↓
                              Response → Client
```

### Panel Orchestration Flow
```
Admin Action (e.g., "Create Account")
         ↓
    Browser POST → hs-srvd (:2086)
         ↓
    JWT Auth Validation
         ↓
    HS::Account->create($params)
         ↓
    ┌────────────────────────────────────────┐
    │ Configuration Engine writes:           │
    │   /var/hspanel/userdata/username/      │
    │   /var/hspanel/users/username.json     │
    └────────────┬───────────────────────────┘
                 ↓
    ┌────────────────────────────────────────┐
    │ System Actions (via C wrappers):       │
    │   useradd → Linux user                 │
    │   mkdir   → /home/username/            │
    │   quota   → disk quota                 │
    └────────────┬───────────────────────────┘
                 ↓
    ┌────────────────────────────────────────┐
    │ Service Rebuilds (Bash scripts):       │
    │   rebuild_httpd.sh  → Apache vhosts    │
    │   rebuild_dns.sh    → Bind zone        │
    │   rebuild_ftp.sh    → FTP config       │
    └────────────┬───────────────────────────┘
                 ↓
    ┌────────────────────────────────────────┐
    │ Service Reloads:                       │
    │   systemctl reload apache2             │
    │   rndc reload                          │
    │   systemctl reload pure-ftpd           │
    └────────────────────────────────────────┘
```

## Component Interconnection Matrix

| Component | Manages | Config Location | Reload Method |
|-----------|---------|-----------------|---------------|
| Apache/Nginx | Virtual hosts, SSL | `/etc/apache2/sites-enabled/` | `systemctl reload` |
| Postfix | SMTP routing, virtual maps | `/etc/postfix/` | `postfix reload` |
| Dovecot | IMAP/POP3, auth | `/etc/dovecot/` | `doveadm reload` |
| Bind9 | DNS zones | `/var/named/` | `rndc reload` |
| MariaDB | Databases, users | `/etc/mysql/` | `mysqladmin reload` |
| PHP-FPM | Per-user pools | `/etc/php/*/fpm/pool.d/` | `systemctl reload php*-fpm` |
| Pure-FTPd | FTP accounts | `/etc/pure-ftpd/` | `systemctl restart pure-ftpd` |
| OpenDKIM | DKIM signing | `/etc/opendkim/` | `systemctl reload opendkim` |
| SpamAssassin | Spam rules | `/etc/spamassassin/` | `systemctl reload spamassassin` |
| certbot | SSL certificates | `/etc/letsencrypt/` | N/A (cron-based) |
