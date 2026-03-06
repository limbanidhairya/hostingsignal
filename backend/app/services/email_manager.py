"""
HostingSignal — Email Manager (Postfix + Dovecot)
Create/manage email accounts, aliases, DKIM/SPF/DMARC.
"""
from .server_utils import run_cmd, write_file, read_file, ensure_dir, DEV_MODE, logger
import hashlib, secrets

VMAIL_DIR = "/home/vmail"
POSTFIX_DIR = "/etc/postfix"
DOVECOT_DIR = "/etc/dovecot"

DEMO_ACCOUNTS = [
    {"email": "admin@example.com", "quota": "1024MB", "used": "256MB", "status": "active"},
    {"email": "info@example.com", "quota": "512MB", "used": "45MB", "status": "active"},
    {"email": "support@example.com", "quota": "512MB", "used": "120MB", "status": "active"},
]

DEMO_ALIASES = [
    {"source": "sales@example.com", "destination": "admin@example.com"},
    {"source": "contact@example.com", "destination": "info@example.com"},
]


def list_accounts(domain: str | None = None) -> list[dict]:
    """List email accounts, optionally filtered by domain."""
    if DEV_MODE:
        if domain:
            return [a for a in DEMO_ACCOUNTS if a["email"].endswith(f"@{domain}")]
        return DEMO_ACCOUNTS
    # Read from Dovecot passwd file
    accounts = []
    passwd = read_file(f"{DOVECOT_DIR}/users") or ""
    for line in passwd.strip().split("\n"):
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            email = parts[0]
            if domain and not email.endswith(f"@{domain}"):
                continue
            accounts.append({"email": email, "quota": "1024MB", "used": "0MB", "status": "active"})
    return accounts


def create_account(email: str, password: str, quota_mb: int = 1024) -> dict:
    """Create a new email account."""
    user, domain = email.split("@")
    maildir = f"{VMAIL_DIR}/{domain}/{user}/Maildir"
    ensure_dir(maildir)

    # Generate password hash (SHA512-CRYPT)
    salt = secrets.token_hex(8)
    if DEV_MODE:
        pw_hash = f"{{SHA512-CRYPT}}$6${salt}$devhash"
    else:
        result = run_cmd(f"doveadm pw -s SHA512-CRYPT -p '{password}'")
        pw_hash = result.stdout.strip() if result.success else f"{{SHA512-CRYPT}}$6${salt}$fallback"

    # Add to Dovecot users file
    line = f"{email}:{pw_hash}:5000:5000::{VMAIL_DIR}/{domain}/{user}::userdb_quota_rule=*:storage={quota_mb}M\n"
    if not DEV_MODE:
        with open(f"{DOVECOT_DIR}/users", "a") as f:
            f.write(line)

    # Add to Postfix virtual mailboxes
    run_cmd(f"echo '{email} {domain}/{user}/Maildir/' >> {POSTFIX_DIR}/vmailbox")
    run_cmd(f"postmap {POSTFIX_DIR}/vmailbox")
    run_cmd("systemctl reload postfix")

    # Set permissions
    run_cmd(f"chown -R 5000:5000 {VMAIL_DIR}/{domain}/{user}")

    return {"email": email, "quota": f"{quota_mb}MB", "used": "0MB", "status": "active"}


def delete_account(email: str) -> bool:
    """Delete an email account."""
    user, domain = email.split("@")
    # Remove from Dovecot users
    run_cmd(f"sed -i '/^{email}:/d' {DOVECOT_DIR}/users")
    # Remove from Postfix vmailbox
    run_cmd(f"sed -i '/^{email}/d' {POSTFIX_DIR}/vmailbox")
    run_cmd(f"postmap {POSTFIX_DIR}/vmailbox")
    # Remove maildir
    run_cmd(f"rm -rf {VMAIL_DIR}/{domain}/{user}")
    run_cmd("systemctl reload postfix")
    return True


def change_password(email: str, new_password: str) -> bool:
    """Change an email account password."""
    if DEV_MODE:
        return True
    result = run_cmd(f"doveadm pw -s SHA512-CRYPT -p '{new_password}'")
    if not result.success:
        return False
    pw_hash = result.stdout.strip()
    # Update in users file
    run_cmd(f"sed -i 's|^{email}:[^:]*:|{email}:{pw_hash}:|' {DOVECOT_DIR}/users")
    return True


def list_aliases(domain: str | None = None) -> list[dict]:
    if DEV_MODE:
        return DEMO_ALIASES
    aliases = []
    content = read_file(f"{POSTFIX_DIR}/virtual") or ""
    for line in content.strip().split("\n"):
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            if domain and not parts[0].endswith(f"@{domain}"):
                continue
            aliases.append({"source": parts[0], "destination": parts[1]})
    return aliases


def add_alias(source: str, destination: str) -> dict:
    """Create an email alias/forwarder."""
    run_cmd(f"echo '{source} {destination}' >> {POSTFIX_DIR}/virtual")
    run_cmd(f"postmap {POSTFIX_DIR}/virtual")
    run_cmd("systemctl reload postfix")
    return {"source": source, "destination": destination}


def delete_alias(source: str) -> bool:
    run_cmd(f"sed -i '/^{source}/d' {POSTFIX_DIR}/virtual")
    run_cmd(f"postmap {POSTFIX_DIR}/virtual")
    run_cmd("systemctl reload postfix")
    return True


def setup_dkim(domain: str) -> dict:
    """Generate DKIM keys for a domain."""
    dkim_dir = f"/etc/opendkim/keys/{domain}"
    ensure_dir(dkim_dir)
    run_cmd(f"opendkim-genkey -D {dkim_dir} -d {domain} -s mail")
    run_cmd(f"chown opendkim:opendkim {dkim_dir}/mail.private")

    # Read the public key for DNS
    pub_key = read_file(f"{dkim_dir}/mail.txt") or "[dev-mode] DKIM key"

    # Add to signing/key tables
    run_cmd(f"echo 'mail._domainkey.{domain} {domain}:mail:{dkim_dir}/mail.private' >> /etc/opendkim/KeyTable")
    run_cmd(f"echo '*@{domain} mail._domainkey.{domain}' >> /etc/opendkim/SigningTable")
    run_cmd("systemctl reload opendkim")

    return {"domain": domain, "selector": "mail", "dns_record": pub_key}
