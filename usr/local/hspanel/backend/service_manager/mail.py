"""
service_manager/mail.py — Postfix + Dovecot mail stack manager
Manages virtual domains, mailboxes, and aliases by writing to
/etc/postfix/virtual_* and /etc/dovecot/users files.
"""
from __future__ import annotations

import re
import os
import logging
import secrets
import string
from pathlib import Path

from .base import BaseServiceManager, ServiceResult

logger = logging.getLogger(__name__)

POSTFIX_CONF         = "/etc/postfix"
VIRTUAL_DOMAINS_FILE = f"{POSTFIX_CONF}/virtual_domains"
VIRTUAL_MAILBOX_FILE = f"{POSTFIX_CONF}/virtual_mailboxes"
VIRTUAL_ALIAS_FILE   = f"{POSTFIX_CONF}/virtual_aliases"
DOVECOT_USERS_FILE   = "/etc/dovecot/users"
MAIL_BASE            = "/var/mail/vhosts"


class MailManager(BaseServiceManager):
    """Manage Postfix virtual domains, mailboxes, and Dovecot auth."""

    # ------------------------------------------------------------------
    # Service control
    # ------------------------------------------------------------------
    def reload_postfix(self) -> ServiceResult:
        rc, out, err = self._sysop("reload_postfix")
        return ServiceResult(rc == 0, out or err)

    def reload_dovecot(self) -> ServiceResult:
        rc, out, err = self._sysop("reload_dovecot")
        return ServiceResult(rc == 0, out or err)

    def reload(self) -> ServiceResult:
        r1 = self.reload_postfix()
        r2 = self.reload_dovecot()
        return ServiceResult(
            r1.success and r2.success,
            f"postfix: {r1.message} | dovecot: {r2.message}",
        )

    def status(self) -> dict:
        return {
            "postfix": self.service_status("postfix"),
            "dovecot": self.service_status("dovecot"),
        }

    # ------------------------------------------------------------------
    # Domain management
    # ------------------------------------------------------------------
    def add_mail_domain(self, domain: str) -> ServiceResult:
        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain: {domain}")

        domains = self._read_lines(VIRTUAL_DOMAINS_FILE)
        if domain in domains:
            return ServiceResult(True, f"Domain already exists: {domain}")

        domains.append(domain)
        self._write_lines(VIRTUAL_DOMAINS_FILE, domains)

        # Create mail storage directory
        mail_dir = Path(f"{MAIL_BASE}/{domain}")
        mail_dir.mkdir(parents=True, exist_ok=True)

        self._postmap(VIRTUAL_DOMAINS_FILE)
        self.reload_postfix()
        return ServiceResult(True, f"Mail domain added: {domain}", {"domain": domain})

    def remove_mail_domain(self, domain: str) -> ServiceResult:
        if not self._validate_domain(domain):
            return ServiceResult(False, f"Invalid domain: {domain}")

        domains = [d for d in self._read_lines(VIRTUAL_DOMAINS_FILE) if d != domain]
        self._write_lines(VIRTUAL_DOMAINS_FILE, domains)

        # Remove all mailboxes for this domain
        mailboxes = self._read_lines(VIRTUAL_MAILBOX_FILE)
        mailboxes = [m for m in mailboxes if not m.endswith(f"@{domain}") and
                     not m.startswith(f"@{domain}")]
        self._write_lines(VIRTUAL_MAILBOX_FILE, mailboxes)

        # Remove from dovecot users
        users = self._read_lines(DOVECOT_USERS_FILE)
        users = [u for u in users if not u.startswith(f"*@{domain}:") and
                 not (len(u.split(":")) > 0 and u.split(":")[0].endswith(f"@{domain}"))]
        self._write_lines(DOVECOT_USERS_FILE, users)

        self._postmap(VIRTUAL_DOMAINS_FILE)
        self._postmap(VIRTUAL_MAILBOX_FILE)
        self.reload()
        return ServiceResult(True, f"Mail domain removed: {domain}")

    def list_mail_domains(self) -> list[str]:
        return self._read_lines(VIRTUAL_DOMAINS_FILE)

    # ------------------------------------------------------------------
    # Mailbox management
    # ------------------------------------------------------------------
    def create_mailbox(
        self, email: str, password: str | None = None, quota_mb: int = 500
    ) -> ServiceResult:
        if not self._validate_email(email):
            return ServiceResult(False, f"Invalid email: {email}")

        user, domain = email.split("@", 1)
        if domain not in self._read_lines(VIRTUAL_DOMAINS_FILE):
            add_result = self.add_mail_domain(domain)
            if not add_result.success:
                return add_result

        password = password or self._generate_password()

        # Virtual mailbox entry: email   domain/user/
        mailboxes = self._read_lines(VIRTUAL_MAILBOX_FILE)
        entry = f"{email}\t{domain}/{user}/"
        if not any(line.startswith(email) for line in mailboxes):
            mailboxes.append(entry)
            self._write_lines(VIRTUAL_MAILBOX_FILE, mailboxes)

        # Dovecot password file: email:{SHA512-CRYPT}hash:uid:gid::/base/dir::
        pw_hash = self._hash_password_doveadm(password)
        if pw_hash:
            users = self._read_lines(DOVECOT_USERS_FILE)
            users = [u for u in users if not u.startswith(f"{email}:")]  # dedup
            users.append(
                f"{email}:{pw_hash}:5000:5000::{MAIL_BASE}/{domain}/{user}::"
                f"userdb_quota_rule=*:storage={quota_mb}M"
            )
            self._write_lines(DOVECOT_USERS_FILE, users)

        # Create maildir
        Path(f"{MAIL_BASE}/{domain}/{user}/Maildir").mkdir(parents=True, exist_ok=True)

        self._postmap(VIRTUAL_MAILBOX_FILE)
        self.reload()
        return ServiceResult(
            True,
            f"Mailbox created: {email}",
            {"email": email, "password": password, "quota_mb": quota_mb},
        )

    def delete_mailbox(self, email: str) -> ServiceResult:
        if not self._validate_email(email):
            return ServiceResult(False, f"Invalid email: {email}")

        mailboxes = [m for m in self._read_lines(VIRTUAL_MAILBOX_FILE)
                     if not m.startswith(email)]
        self._write_lines(VIRTUAL_MAILBOX_FILE, mailboxes)

        users = [u for u in self._read_lines(DOVECOT_USERS_FILE)
                 if not u.startswith(f"{email}:")]
        self._write_lines(DOVECOT_USERS_FILE, users)

        self._postmap(VIRTUAL_MAILBOX_FILE)
        self.reload()
        return ServiceResult(True, f"Mailbox deleted: {email}")

    def list_mailboxes(self, domain: str | None = None) -> list[str]:
        mailboxes = []
        for line in self._read_lines(VIRTUAL_MAILBOX_FILE):
            parts = line.split()
            if parts:
                email = parts[0]
                if domain is None or email.endswith(f"@{domain}"):
                    mailboxes.append(email)
        return mailboxes

    def change_mailbox_password(self, email: str, new_password: str) -> ServiceResult:
        users = self._read_lines(DOVECOT_USERS_FILE)
        pw_hash = self._hash_password_doveadm(new_password)
        if not pw_hash:
            return ServiceResult(False, "Could not hash password (doveadm not available)")

        updated = []
        found = False
        for line in users:
            if line.startswith(f"{email}:"):
                parts = line.split(":")
                parts[1] = pw_hash
                updated.append(":".join(parts))
                found = True
            else:
                updated.append(line)

        if not found:
            return ServiceResult(False, f"Mailbox not found: {email}")

        self._write_lines(DOVECOT_USERS_FILE, updated)
        self.reload_dovecot()
        return ServiceResult(True, f"Password changed for: {email}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _postmap(self, file_path: str) -> None:
        self._run(["postmap", file_path], timeout=15)

    def _hash_password_doveadm(self, password: str) -> str:
        rc, out, _ = self._run(
            ["doveadm", "pw", "-s", "SHA512-CRYPT", "-p", password], timeout=10
        )
        return out.strip() if rc == 0 else ""

    def _read_lines(self, path: str) -> list[str]:
        p = Path(path)
        if not p.exists():
            return []
        return [l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")]

    def _write_lines(self, path: str, lines: list[str]) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines) + "\n")

    @staticmethod
    def _validate_domain(domain: str) -> bool:
        return bool(re.match(r'^(?!-)[A-Za-z0-9\-]{1,63}(?<!-)(\.[A-Za-z0-9\-]{1,63})+$', domain))

    @staticmethod
    def _validate_email(email: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))

    @staticmethod
    def _generate_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
