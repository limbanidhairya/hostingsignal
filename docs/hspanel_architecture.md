# HS-Panel Architecture Blueprint

This document details the architectural design for **HS-Panel**, a traditional, production-grade Linux hosting control panel built using a resilient stack of Perl, C/C++, and Bash, alongside a modern HTML/CSS/JavaScript frontend. It avoids proprietary implementations of existing panels while delivering a robust, automated hosting ecosystem.

---

## PHASE 1: FULL HS-PANEL ARCHITECTURE

At a high level, HS-Panel operates as a localized monolithic orchestrator running on a single Linux server. It decouples the user interface from the high-privilege system modifications using a strict API and socket boundary.

*   **Control Panel UI**: Lightweight HTML/CSS/JS applications served by a custom local web server. It connects asynchronously to the backend API.
*   **Backend API Layer**: A persistent Perl FastCGI/HTTP daemon (`hs-srvd`) that listens on specific ports (e.g., 2082 for users, 2086 for admins). It receives JSON payloads, validates sessions, and dispatches requests to the Service Management Layer.
*   **Service Management Layer**: A series of Perl modules (`HS::Account`, `HS::Mail`, `HS::DNS`) that contain the business logic for standard operations.
*   **Configuration Engine**: A flat-file text parsing engine located in `/var/hspanel/userdata/` that maintains the desired state of domains, databases, and mail accounts.
*   **Task Queue System**: A local queuing mechanism (using a lightweight queue broker or file-based queue) that accepts long-running tasks for background execution.
*   **Daemon Services**: Internal worker processes (`hs-taskd`, `hs-logd`) that execute queue items and monitor system health.
*   **Plugin System**: A standardized hook system where pre- and post-action events execute custom scripts placed in `/usr/local/hspanel/plugins/`.

Communication flow: `Browser -> (Port 2082) hs-srvd -> HS::* Modules -> C-Wrappers (setuid) -> System Binaries / Bash Scripts`.

---

## PHASE 2: CORE FEATURES

The architecture inherently supports the following subsystems through dedicated integration modules:

*   **Account Management**: Manages Linux user creation (`useradd`), filesystem quotas, and user-level directory skeletons.
*   **Domain Management**: Handles parked domains, add-on domains, and subdomains by updating the configuration engine and triggering web server rebuilds.
*   **Mail Server Management**: Orchestrates MTA and IMAP/POP3 configurations, alongside localized spam filtering configurations.
*   **DNS Management**: Constructs structured zone files for local authoritative nameservers and manages serialization.
*   **Database Management**: Connects via local sockets to MySQL/MariaDB and PostgreSQL to provision users, databases, and exact privilege grants.
*   **File Manager**: A secure interface interpreting frontend standard protocols into localized filesystem operations, guarded by strict permissions.
*   **SSL Management**: Certificate parsing, validation, installation, and integration with Let's Encrypt for automatic provisioning (AutoSSL).
*   **Backup System**: A scheduled differential/full backup runner utilizing `tar` and `rsync` targeting local drives or remote SSH/S3 destinations.
*   **Cron Job Scheduler**: A secure wrapper for `/var/spool/cron` enabling users to safely define their own crontabs.
*   **Server Monitoring**: Real-time extraction of `/proc` metrics (load, RAM) alongside network socket validation to ensure dependent services (Apache, MySQL) stay alive.

---

## PHASE 3: MAIL SERVER SYSTEM

The HS-Panel email stack uses industry-standard, robust open-source mail agents.

*   **SMTP Server**: `Postfix` (default) or `Exim`. HS-Panel writes virtual map configurations to `/etc/postfix/vmailbox` or Exim flat-files mapping domains to local delivery directories.
*   **IMAP / POP3 Server**: `Dovecot` is used for mail retrieval. It utilizes a `passwd-file` authentication driver targeting `/etc/hspanel/mail/domain.com/passwd` which HS-Panel manages securely.
*   **Spam Filtering**: `SpamAssassin` integrated via `spamd`/`spamc` in the postfix/exim pipe, assigning spam scores configured globally and per-user.
*   **DKIM / SPF Configuration**: DNS validation is baked in. `OpenDKIM` runs to sign outbound emails automatically when new domains are provisioned.

**Capabilities**:
*   *Create Accounts*: `HS::Mail->create()` generates Dovecot hashes and appends them to domain-specific virtual maps.
*   *Mailbox Quotas*: Handled via Dovecot quota dicts written by the backend.
*   *Forwarders/Aliases*: Handled by virtual alias maps parsed safely by Postfix/Exim.
*   *Autoresponders*: Processed through a localized sieve script or a custom perl pipe script handling vacation responses.

---

## PHASE 4: DNS MANAGEMENT

The authoritative DNS capability is handled primarily by **Bind9** (named), with architectural abstractions allowing for **PowerDNS**.

*   **Configurations**: For Bind, HS-Panel writes standard RFC 1035 zone files to `/var/named/` and updates `/etc/named.conf` or `/etc/named/hspanel-zones.conf`.
*   **Capabilities**:
    *   *Create Zones*: Triggered during account creation. Serializes SOA, NS, A, and MX records dynamically.
    *   *Edit Records*: API calls modify the zone file using regex/parsing arrays, increments the serial via POSIX timestamps, and issues `rndc reload <domain>`.
    *   *Templates*: Administrators define standard templates in `/usr/local/hspanel/templates/dns/`.

---

## PHASE 5: FILE MANAGER

A responsive React/Vue or vanilla JS File Manager interacting with `/api/fileman/` over JSON.

*   **Security Boundary**: Because `hs-srvd` runs as root, file operations are passed through a tightly controlled C-wrapper (`wrap_fileop.c`) which executes `setuid(user_id)` before interacting with the local disk. It restricts operations outside of `/home/user/`.
*   **Capabilities**:
    *   *Upload/Download*: Standard chunked HTTP transfers.
    *   *Extract*: Triggers `unzip` or `tar` as the respective user via background forks.
    *   *Permissions*: Direct abstraction of `chmod` and `chown`.

---

## PHASE 6: WEB SERVER MANAGEMENT

HS-Panel acts as an agnostic configuration generator for **Apache**, **Nginx**, and **OpenLiteSpeed**.

*   **Core Flow**: Instead of editing `httpd.conf` live, HS-Panel alters metadata in `/var/hspanel/userdata/$user/$domain`. A Perl script `rebuild_web_configs.pl` reads these files and compiles a master template.
*   **Capabilities**:
    *   *Virtual Hosts*: Templates combine static headers with dynamic DocumentRoots.
    *   *PHP Versions*: Implements `php-fpm` pools. HS-Panel creates a unique UNIX socket for each user (`/sock/php-fpm/user-8.1.sock`) and points the vhost to it.

---

## PHASE 7: LINUX SERVICE AUTOMATION

An abstraction layer defining service lifecycles.

*   **Engine**: `HS::System` interfaces with `systemd` (or `sysvinit` via `service`).
*   **Automation**:
    *   Restart policies: Changes to Apache configuration trigger a syntax check (`apachectl configtest`). If successful, `systemctl reload apache2` is executed. If failed, it rolls back to a safe snapshot and issues an alert.
    *   Implemented via `Bash` wrappers stored in `/usr/local/hspanel/scripts/`.

---

## PHASE 8 & 9: FOLDER STRUCTURE & INSTALLER DESIGN

**Universal Installer Responsibilities:**
The installer fetches a lightweight bash script (`install.sh`) which detects `/etc/os-release`. It maps standard packages (e.g., `httpd` for RHEL, `apache2` for Ubuntu) and initiates package managers (`apt`, `dnf`), installs a local Perl environment (to prevent OS perl version conflicts), compiles the C wrappers, and boots systemd units.

**Filesystem Layout:**
```text
/usr/local/hspanel/
├── api/          # Universal entrypoint for HTTP REST calls (routing)
├── bin/          # Compiled C binaries (setuid wrappers)
├── config/       # Panel's internal configurations (ports, db passwords)
├── daemon/       # Core Perl daemons (hs-srvd, hs-taskd)
├── logs/         # Access logs, error logs, and task queue stdout
├── perl/         # Internal Perl modules (HS::Core, HS::Admin)
├── plugins/      # Third-party bash/perl add-ons modifying core behavior
├── scripts/      # Bash automation scripts (restart_apache, pkg_install)
├── templates/    # UI Templates and Service templates (vhost.tmpl)
└── ui/           # Static frontend assets (HTML, CSS, JS)

/var/hspanel/
├── userdata/     # State configuration for accounts and domains
└── users/        # Flat-file listing of username -> UID/Plan mappings
```

---

## PHASE 10: UNIVERSAL INSTALLER SCRIPT

Below is an abbreviated template of the universal installation payload.

```bash
#!/bin/bash
# HS-Panel Universal Installer
set -e

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "Unsupported OS" && exit 1
fi

echo "Installing HS-Panel on $OS $VERSION..."

# 2. Install Dependencies
if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
    apt-get update && apt-get install -y gcc make perl libio-socket-ssl-perl libjson-perl \
    apache2 bind9 postfix dovecot-imapd mariadb-server curl
elif [[ "$OS" == "almalinux" || "$OS" == "rocky" ]]; then
    dnf install -y gcc make perl perl-IO-Socket-SSL perl-JSON \
    httpd bind postfix dovecot mariadb-server curl
fi

# 3. Create Filesystem
mkdir -p /usr/local/hspanel/{api,bin,config,daemon,logs,perl,scripts,ui,templates}
mkdir -p /var/hspanel/{userdata,users}

# 4. Compile C Wrappers
# gcc -O2 -o /usr/local/hspanel/bin/wrapper /usr/local/hspanel/src/wrapper.c
# chmod 4755 /usr/local/hspanel/bin/wrapper

# 5. Download Core
# curl -sL https://download.hspanel.com/core.tar.gz | tar xz -C /usr/local/hspanel/

# 6. Configure Systemd
cat <<EOF > /etc/systemd/system/hspanel.service
[Unit]
Description=HS-Panel Daemon
After=network.target

[Service]
ExecStart=/usr/bin/perl /usr/local/hspanel/daemon/hs-srvd.pl
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hspanel
systemctl start hspanel

echo "HS-Panel Installation Complete! Port: 2086"
```

---

## PHASE 11: TASK QUEUE SYSTEM

Tasks that take longer than 5 seconds are detrimental to HTTP API connections. 
*   **Implementation**: A custom filesystem queue (`/var/hspanel/queue/`) or a lightweight Redis instance.
*   **Flow**: When a user clicks "Generate Backup", `hs-srvd` writes a JSON payload to the queue directory and returns immediately with a `job_id`. The daemon `hs-taskd` watches this directory continuously, locking files exclusively, executing the heavy Bash/Perl scripts (e.g., executing `tar`), and updating a `/var/hspanel/queue/done/` status file the UI can poll.

---

## PHASE 12: SECURITY ARCHITECTURE

1.  **Privilege Separation**: The web GUI cannot perform operations directly. `hs-srvd` drops privileges or explicitly requires calls to C wrappers (`setuid` binaries) to execute commands.
2.  **API Authentication**: Managed utilizing stateless JWT tokens or cryptographic API keys generated by WHM.
3.  **Jailed Filesystem**: Shell users are configured with `jailkit` or `cagefs` equivalents, isolating SSH/SFTP spaces to block seeing other `/home/*` contexts.

---

## PHASE 13: PLUGIN SDK

Developers create a directory in `/usr/local/hspanel/plugins/myplugin/`.
Inside, an `install.json` binds the plugin to UI menu hooks.
**Event Hooks**: `hs-srvd` allows developers to intercept system events. For example, a script placed at `/usr/local/hspanel/hooks/post_createacct` is executed automatically via standard output piping whenever a new user is provisioned, enabling automation like inserting billing records remotely.

---

## PHASE 14: MICROSERVICE UPGRADE PATH

For scaling out of the localized monolithic constraints towards thousands of servers, HS-Panel can adopt a **Control-Plane/Data-Plane** architecture.

*   **Central Control Plane (Kubernetes/Docker)**:
    *   *User Service*: Global authentication and SSO.
    *   *DNS Service*: A distributed microservice utilizing PowerDNS API to cluster global DNS zones.
    *   *Database Service*: Provisions MySQL grants dynamically on independent DB clusters.
*   **Data Plane (Host Nodes)**:
    *   The traditional `hs-srvd` is stripped down to an "Agent" model (`hs-agent`). It only listens on internal networks, receiving gRPC/REST instructions from the Central Control Plane to create user mounts, restart local Apache, or write Vhost YAMLs. High availability is achieved because web hosting nodes contain no central database—they are purely disposable execute engines for the Microservice Plane.
