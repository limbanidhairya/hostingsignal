#!/usr/bin/env bash
set -euo pipefail

# Mail provisioning engine.
# Workflow:
# create mailbox dir -> postfix maps -> dovecot auth -> db auth row -> reload services

MAIL_ROOT="${MAIL_ROOT:-/home/mail}"
VMAILBOX_FILE="${VMAILBOX_FILE:-/etc/postfix/vmailbox}"
VMAILBOX_DB="${VMAILBOX_DB:-/etc/postfix/vmailbox.db}"
DOVECOT_USERS="${DOVECOT_USERS:-/etc/dovecot/users}"
PANEL_DB="${PANEL_DB:-hspanel}"

usage() {
  cat <<EOF
Usage:
  $0 <domain> <user> <password>
Example:
  $0 example.com admin S3cureP@ss
EOF
}

validate_domain() {
  local d="$1"
  [[ "$d" =~ ^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$ ]] || { echo "Invalid domain" >&2; exit 1; }
}

validate_user() {
  local u="$1"
  [[ "$u" =~ ^[a-zA-Z0-9._-]+$ ]] || { echo "Invalid mailbox user" >&2; exit 1; }
}

ensure_postfix_maps() {
  touch "$VMAILBOX_FILE"
  touch "$DOVECOT_USERS"
}

create_mailbox_dir() {
  local domain="$1"
  local user="$2"
  local mailbox_dir="${MAIL_ROOT}/${domain}/${user}/Maildir"

  mkdir -p "$mailbox_dir"/{cur,new,tmp}
  chmod -R 750 "${MAIL_ROOT}/${domain}"
}

configure_postfix_domain() {
  local domain="$1"
  local user="$2"

  if ! grep -qE "^${domain}(\s|$)" /etc/postfix/virtual_mailbox_domains 2>/dev/null; then
    echo "$domain" >> /etc/postfix/virtual_mailbox_domains
  fi

  postmap /etc/postfix/virtual_mailbox_domains

  if ! grep -qE "^${user}@${domain}(\s|$)" "$VMAILBOX_FILE" 2>/dev/null; then
    echo "${user}@${domain} ${domain}/${user}/Maildir/" >> "$VMAILBOX_FILE"
  fi

  postmap "$VMAILBOX_FILE"

  postconf -e "virtual_mailbox_domains = hash:/etc/postfix/virtual_mailbox_domains"
  postconf -e "virtual_mailbox_maps = hash:${VMAILBOX_FILE}"
  postconf -e "virtual_transport = lmtp:unix:private/dovecot-lmtp"
}

configure_dovecot_user() {
  local domain="$1"
  local user="$2"
  local password="$3"

  local hash
  hash="$(doveadm pw -s SHA512-CRYPT -p "$password")"

  if grep -qE "^${user}@${domain}:" "$DOVECOT_USERS" 2>/dev/null; then
    sed -i "s|^${user}@${domain}:.*|${user}@${domain}:${hash}:5000:5000::${MAIL_ROOT}/${domain}/${user}::userdb_mail=maildir:${MAIL_ROOT}/${domain}/${user}/Maildir|" "$DOVECOT_USERS"
  else
    echo "${user}@${domain}:${hash}:5000:5000::${MAIL_ROOT}/${domain}/${user}::userdb_mail=maildir:${MAIL_ROOT}/${domain}/${user}/Maildir" >> "$DOVECOT_USERS"
  fi

  chmod 640 "$DOVECOT_USERS"
}

create_db_auth_entry() {
  local domain="$1"
  local user="$2"
  local password="$3"

  mysql --defaults-file=/root/.my.cnf "$PANEL_DB" <<SQL
CREATE TABLE IF NOT EXISTS mail_accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  domain VARCHAR(255) NOT NULL,
  username VARCHAR(255) NOT NULL,
  password_plain VARCHAR(255) NOT NULL,
  mailbox_path VARCHAR(512) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_mailbox (domain, username)
);
INSERT INTO mail_accounts (domain, username, password_plain, mailbox_path)
VALUES ('${domain}', '${user}', '${password}', '${MAIL_ROOT}/${domain}/${user}/Maildir')
ON DUPLICATE KEY UPDATE
  password_plain=VALUES(password_plain),
  mailbox_path=VALUES(mailbox_path);
SQL
}

main() {
  [[ $# -eq 3 ]] || { usage; exit 1; }
  local domain="$1"
  local user="$2"
  local password="$3"

  validate_domain "$domain"
  validate_user "$user"
  ensure_postfix_maps
  create_mailbox_dir "$domain" "$user"
  configure_postfix_domain "$domain" "$user"
  configure_dovecot_user "$domain" "$user" "$password"
  create_db_auth_entry "$domain" "$user" "$password"

  systemctl reload postfix || systemctl restart postfix
  systemctl reload dovecot || systemctl restart dovecot

  echo "Mail account provisioned: ${user}@${domain}"
  echo "Mailbox path: ${MAIL_ROOT}/${domain}/${user}/Maildir"
}

main "$@"
