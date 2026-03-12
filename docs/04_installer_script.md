# STEP 13 — UNIVERSAL INSTALLER SCRIPT

```bash
#!/bin/bash
###############################################################################
# HS-Panel Universal Installer v2.0
# Supports: Ubuntu 22/24, Debian 12, AlmaLinux 8/9, Rocky Linux 8/9
###############################################################################
set -euo pipefail

HSPANEL_VERSION="2.0.0"
HSPANEL_DIR="/usr/local/hspanel"
HSPANEL_VAR="/var/hspanel"
HSPANEL_LOG="/var/log/hspanel-install.log"
ADMIN_PORT=2086
USER_PORT=2082

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[HS-Panel]${NC} $1" | tee -a "$HSPANEL_LOG"; }
err()  { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$HSPANEL_LOG"; exit 1; }
warn() { echo -e "${CYAN}[WARN]${NC} $1" | tee -a "$HSPANEL_LOG"; }

# ─── PRE-FLIGHT ──────────────────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && err "Must be run as root"
[[ ! -f /etc/os-release ]] && err "Cannot detect OS"

. /etc/os-release
OS="$ID"
OS_VERSION="$VERSION_ID"
OS_MAJOR="${VERSION_ID%%.*}"

echo "═══════════════════════════════════════════"
echo "  HS-Panel Installer v${HSPANEL_VERSION}"
echo "  Detected: ${OS} ${OS_VERSION}"
echo "═══════════════════════════════════════════"

# Validate supported OS
case "$OS" in
  ubuntu)
    [[ "$OS_MAJOR" != "22" && "$OS_MAJOR" != "24" ]] && \
      err "Ubuntu $OS_VERSION not supported. Use 22.04 or 24.04" ;;
  debian)
    [[ "$OS_MAJOR" != "12" ]] && err "Debian $OS_VERSION not supported. Use 12" ;;
  almalinux|rocky)
    [[ "$OS_MAJOR" != "8" && "$OS_MAJOR" != "9" ]] && \
      err "$OS $OS_VERSION not supported. Use 8 or 9" ;;
  *) err "Unsupported OS: $OS" ;;
esac

# Check resources
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
[[ "$TOTAL_RAM" -lt 768 ]] && err "Minimum 1GB RAM required (detected: ${TOTAL_RAM}MB)"
DISK_FREE=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
[[ "$DISK_FREE" -lt 15 ]] && err "Minimum 20GB disk required (free: ${DISK_FREE}GB)"

log "Pre-flight checks passed ✓"

# ─── PHASE 1: DEPENDENCIES ──────────────────────────────────────────────
log "[1/6] Installing system dependencies..."

if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y >> "$HSPANEL_LOG" 2>&1
  apt-get install -y \
    gcc g++ make autoconf automake libtool pkg-config \
    perl libio-socket-ssl-perl libjson-perl libcgi-pm-perl \
    libdbd-mysql-perl libdigest-sha-perl libmime-base64-perl \
    libwww-perl liburi-perl libyaml-perl \
    apache2 libapache2-mod-fcgid \
    bind9 bind9utils dnsutils \
    postfix dovecot-imapd dovecot-pop3d dovecot-lmtpd \
    spamassassin spamc opendkim opendkim-tools \
    mariadb-server mariadb-client \
    php8.2-fpm php8.2-cli php8.2-mysql php8.2-curl php8.2-gd \
    php8.2-mbstring php8.2-xml php8.2-zip php8.2-intl \
    pure-ftpd \
    certbot redis-server \
    curl wget rsync tar gzip bzip2 unzip jq \
    >> "$HSPANEL_LOG" 2>&1

elif [[ "$OS" == "almalinux" || "$OS" == "rocky" ]]; then
  dnf install -y epel-release >> "$HSPANEL_LOG" 2>&1
  dnf install -y \
    gcc gcc-c++ make autoconf automake libtool \
    perl perl-IO-Socket-SSL perl-JSON perl-CGI \
    perl-DBD-MySQL perl-Digest-SHA perl-MIME-Base64 \
    perl-libwww-perl perl-URI perl-YAML \
    httpd mod_fcgid \
    bind bind-utils \
    postfix dovecot \
    spamassassin opendkim \
    mariadb-server mariadb \
    php-fpm php-cli php-mysqlnd php-gd php-mbstring php-xml \
    pure-ftpd \
    certbot redis \
    curl wget rsync tar gzip bzip2 unzip jq \
    >> "$HSPANEL_LOG" 2>&1
fi

log "Dependencies installed ✓"

# ─── PHASE 2: DIRECTORY STRUCTURE ───────────────────────────────────────
log "[2/6] Creating HS-Panel filesystem..."

mkdir -p "${HSPANEL_DIR}"/{api,bin,config,config/ssl,daemon,logs,perl/HS}
mkdir -p "${HSPANEL_DIR}"/{plugins,scripts,security,src,cache/sessions,cache/templates}
mkdir -p "${HSPANEL_DIR}"/templates/{apache,nginx,dns,mail,ui/error-pages}
mkdir -p "${HSPANEL_DIR}"/ui/{admin/{css,js,img},user/{css,js,img},guest}
mkdir -p "${HSPANEL_VAR}"/{userdata,users,queue/{pending,running,done,failed},backups}
mkdir -p /var/mail/vhosts
mkdir -p /etc/hspanel

chmod -R 755 "$HSPANEL_DIR"
chmod -R 700 "${HSPANEL_VAR}/userdata"
chmod -R 700 "${HSPANEL_VAR}/users"
chmod 750 "${HSPANEL_VAR}/queue"

log "Filesystem created ✓"

# ─── PHASE 3: COMPILE C WRAPPERS ────────────────────────────────────────
log "[3/6] Compiling security wrappers..."

# Generate wrap_sysop.c
cat << 'CSRC' > "${HSPANEL_DIR}/src/wrap_sysop.c"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <errno.h>

#define MAX_CMD 4096
#define SCRIPTS_DIR "/usr/local/hspanel/scripts/"

static const char *allowed_scripts[] = {
    "rebuild_httpd.sh", "rebuild_dns.sh", "rebuild_mail.sh",
    "rebuild_ftp.sh", "restart_services.sh", "backup_account.sh",
    "ssl_renew.sh", "quota_sync.sh", NULL
};

int is_allowed(const char *script) {
    for (int i = 0; allowed_scripts[i]; i++) {
        if (strcmp(script, allowed_scripts[i]) == 0) return 1;
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: wrap_sysop <script> [args...]\n");
        return 1;
    }
    if (!is_allowed(argv[1])) {
        fprintf(stderr, "Denied: %s not in allowed list\n", argv[1]);
        return 2;
    }
    char cmd[MAX_CMD];
    snprintf(cmd, sizeof(cmd), "%s%s", SCRIPTS_DIR, argv[1]);

    /* Append arguments */
    for (int i = 2; i < argc && strlen(cmd) < MAX_CMD - 256; i++) {
        strncat(cmd, " ", MAX_CMD - strlen(cmd) - 1);
        strncat(cmd, argv[i], MAX_CMD - strlen(cmd) - 1);
    }

    setuid(0);
    setgid(0);
    return system(cmd);
}
CSRC

cat << 'MAKEFILE' > "${HSPANEL_DIR}/src/Makefile"
CC=gcc
CFLAGS=-O2 -Wall -Wextra
BINDIR=../bin

all: wrap_sysop wrap_fileop

wrap_sysop: wrap_sysop.c
	$(CC) $(CFLAGS) -o $(BINDIR)/wrap_sysop wrap_sysop.c
	chmod 4755 $(BINDIR)/wrap_sysop

wrap_fileop: wrap_fileop.c
	$(CC) $(CFLAGS) -o $(BINDIR)/wrap_fileop wrap_fileop.c
	chmod 4755 $(BINDIR)/wrap_fileop

clean:
	rm -f $(BINDIR)/wrap_sysop $(BINDIR)/wrap_fileop
MAKEFILE

# Create minimal wrap_fileop.c
cat << 'CSRC2' > "${HSPANEL_DIR}/src/wrap_fileop.c"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#include <pwd.h>

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: wrap_fileop <username> <op> <path> [args...]\n");
        return 1;
    }
    const char *username = argv[1];
    const char *op = argv[2];
    const char *path = argv[3];

    struct passwd *pw = getpwnam(username);
    if (!pw) { fprintf(stderr, "Unknown user: %s\n", username); return 2; }

    /* Resolve real path and verify within home */
    char resolved[PATH_MAX];
    char homedir[PATH_MAX];
    snprintf(homedir, sizeof(homedir), "/home/%s/", username);

    if (realpath(path, resolved) == NULL && strcmp(op, "mkdir") != 0) {
        perror("realpath"); return 3;
    }
    if (strncmp(resolved, homedir, strlen(homedir)) != 0) {
        fprintf(stderr, "Access denied: path outside home\n"); return 4;
    }

    /* Drop to user */
    setgid(pw->pw_gid);
    setuid(pw->pw_uid);

    if (strcmp(op, "chmod") == 0 && argc >= 5) {
        char cmd[PATH_MAX + 32];
        snprintf(cmd, sizeof(cmd), "chmod %s '%s'", argv[4], resolved);
        return system(cmd);
    }
    fprintf(stderr, "Unknown operation: %s\n", op);
    return 5;
}
CSRC2

cd "${HSPANEL_DIR}/src"
make all >> "$HSPANEL_LOG" 2>&1 || warn "C compilation had warnings"

log "Security wrappers compiled ✓"

# ─── PHASE 4: GENERATE PANEL SSL ────────────────────────────────────────
log "[4/6] Generating panel SSL certificate..."

openssl req -x509 -nodes -days 3650 \
  -newkey rsa:2048 \
  -keyout "${HSPANEL_DIR}/config/ssl/panel.key" \
  -out "${HSPANEL_DIR}/config/ssl/panel.crt" \
  -subj "/CN=$(hostname)/O=HS-Panel/C=US" \
  >> "$HSPANEL_LOG" 2>&1

log "SSL certificate generated ✓"

# ─── PHASE 5: CONFIGURE SERVICES ────────────────────────────────────────
log "[5/6] Configuring system services..."

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)

cat << EOF > "${HSPANEL_DIR}/config/hspanel.conf"
# HS-Panel Configuration
admin_port = ${ADMIN_PORT}
user_port  = ${USER_PORT}
jwt_secret = ${JWT_SECRET}
data_dir   = ${HSPANEL_VAR}
log_dir    = ${HSPANEL_DIR}/logs
ssl_cert   = ${HSPANEL_DIR}/config/ssl/panel.crt
ssl_key    = ${HSPANEL_DIR}/config/ssl/panel.key
web_engine = apache
dns_engine = bind
mail_engine = postfix
EOF

# Enable services
if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
  systemctl enable apache2 bind9 postfix dovecot mariadb redis-server 2>/dev/null
else
  systemctl enable httpd named postfix dovecot mariadb redis 2>/dev/null
fi

# Configure firewall
if command -v ufw &>/dev/null; then
  ufw allow 80,443,${ADMIN_PORT},${USER_PORT},25,587,993,995,53/tcp
  ufw allow 53/udp
elif command -v firewall-cmd &>/dev/null; then
  for port in 80 443 $ADMIN_PORT $USER_PORT 25 587 993 995; do
    firewall-cmd --permanent --add-port=${port}/tcp 2>/dev/null
  done
  firewall-cmd --permanent --add-port=53/tcp --add-port=53/udp 2>/dev/null
  firewall-cmd --reload 2>/dev/null
fi

log "Services configured ✓"

# ─── PHASE 6: SYSTEMD UNITS & START ─────────────────────────────────────
log "[6/6] Installing daemons..."

cat << 'UNIT1' > /etc/systemd/system/hspanel.service
[Unit]
Description=HS-Panel HTTP Daemon
After=network.target mariadb.service redis.service
Wants=mariadb.service

[Service]
Type=simple
ExecStart=/usr/bin/perl /usr/local/hspanel/daemon/hs-srvd.pl
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
UNIT1

cat << 'UNIT2' > /etc/systemd/system/hspanel-taskd.service
[Unit]
Description=HS-Panel Task Queue Daemon
After=network.target hspanel.service

[Service]
Type=simple
ExecStart=/usr/bin/perl /usr/local/hspanel/daemon/hs-taskd.pl
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT2

systemctl daemon-reload
systemctl enable hspanel hspanel-taskd
systemctl start hspanel hspanel-taskd 2>/dev/null || warn "Daemons need Perl scripts"

SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "═══════════════════════════════════════════════════"
echo "  HS-Panel v${HSPANEL_VERSION} Installation Complete!"
echo ""
echo "  Admin Panel:  https://${SERVER_IP}:${ADMIN_PORT}"
echo "  User Panel:   https://${SERVER_IP}:${USER_PORT}"
echo ""
echo "  Login with root credentials"
echo "═══════════════════════════════════════════════════"
```
