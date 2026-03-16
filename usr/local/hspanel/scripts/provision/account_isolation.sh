#!/usr/bin/env bash
set -euo pipefail

# Account isolation and resource limits.
# Creates isolated account tree and applies quotas/limits metadata.

USERS_ROOT="${USERS_ROOT:-/home/users}"
LIMITS_DIR="${LIMITS_DIR:-/etc/hostingsignal/users}"
PANEL_DB="${PANEL_DB:-hspanel}"

usage() {
  cat <<EOF
Usage:
  $0 <username> [disk_mb] [domain_limit] [email_limit] [db_limit]
Example:
  $0 user1 10240 20 100 30
EOF
}

validate_user() {
  local user="$1"
  [[ "$user" =~ ^[a-z_][a-z0-9_-]{1,31}$ ]] || {
    echo "Invalid username: $user" >&2
    exit 1
  }
}

ensure_system_user() {
  local user="$1"
  if ! id "$user" >/dev/null 2>&1; then
    useradd -m -d "${USERS_ROOT}/${user}" -s /bin/bash "$user"
  fi

  mkdir -p "${USERS_ROOT}/${user}/domains"
  chown -R "$user":"$user" "${USERS_ROOT}/${user}"
  chmod 750 "${USERS_ROOT}/${user}"
}

apply_quota_if_possible() {
  local user="$1"
  local disk_mb="$2"

  if command -v setquota >/dev/null 2>&1; then
    local blocks
    blocks=$((disk_mb * 1024))
    setquota -u "$user" "$blocks" "$blocks" 0 0 / || true
  fi
}

write_limits_file() {
  local user="$1"
  local disk_mb="$2"
  local domain_limit="$3"
  local email_limit="$4"
  local db_limit="$5"

  mkdir -p "$LIMITS_DIR"
  cat > "${LIMITS_DIR}/${user}.limits" <<EOF
username=${user}
disk_quota_mb=${disk_mb}
domain_limit=${domain_limit}
email_limit=${email_limit}
database_limit=${db_limit}
EOF
  chmod 640 "${LIMITS_DIR}/${user}.limits"
}

persist_limits_db() {
  local user="$1"
  local disk_mb="$2"
  local domain_limit="$3"
  local email_limit="$4"
  local db_limit="$5"

  mysql --defaults-file=/root/.my.cnf "$PANEL_DB" <<SQL
CREATE TABLE IF NOT EXISTS account_limits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  disk_quota_mb INT NOT NULL,
  domain_limit INT NOT NULL,
  email_limit INT NOT NULL,
  database_limit INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
INSERT INTO account_limits (username, disk_quota_mb, domain_limit, email_limit, database_limit)
VALUES ('${user}', ${disk_mb}, ${domain_limit}, ${email_limit}, ${db_limit})
ON DUPLICATE KEY UPDATE
  disk_quota_mb=VALUES(disk_quota_mb),
  domain_limit=VALUES(domain_limit),
  email_limit=VALUES(email_limit),
  database_limit=VALUES(database_limit);
SQL
}

main() {
  [[ $# -ge 1 ]] || { usage; exit 1; }

  local user="$1"
  local disk_mb="${2:-5120}"
  local domain_limit="${3:-10}"
  local email_limit="${4:-50}"
  local db_limit="${5:-20}"

  validate_user "$user"
  ensure_system_user "$user"
  apply_quota_if_possible "$user" "$disk_mb"
  write_limits_file "$user" "$disk_mb" "$domain_limit" "$email_limit" "$db_limit"
  persist_limits_db "$user" "$disk_mb" "$domain_limit" "$email_limit" "$db_limit"

  echo "Account isolation configured for ${user}"
  echo "Home: ${USERS_ROOT}/${user}"
}

main "$@"
