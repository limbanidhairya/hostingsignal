#!/usr/bin/env bash
set -euo pipefail

# DNS automation engine for PowerDNS + MariaDB backend.
# Usage:
#   dns_engine.sh create-zone example.com
#   dns_engine.sh add-record example.com www A 1.2.3.4 3600

PDNS_DB="${PDNS_DB:-pdns}"
ZONE_DIR="${ZONE_DIR:-/etc/powerdns/zones}"

usage() {
  cat <<EOF
Usage:
  $0 create-zone <domain>
  $0 add-record <domain> <name> <type> <content> [ttl] [prio]
EOF
}

require_root() {
  [[ "$(id -u)" -eq 0 ]] || { echo "Run as root" >&2; exit 1; }
}

validate_domain() {
  local d="$1"
  [[ "$d" =~ ^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$ ]] || {
    echo "Invalid domain: $d" >&2
    exit 1
  }
}

mysql_exec() {
  mysql --defaults-file=/root/.my.cnf "$@"
}

ensure_zone_file() {
  local domain="$1"
  mkdir -p "$ZONE_DIR"
  cat > "$ZONE_DIR/${domain}.zone" <<EOF
$TTL 3600
@   IN  SOA ns1.${domain}. hostmaster.${domain}. (
        $(date +%Y%m%d%H) 3600 900 1209600 3600 )
@   IN  NS  ns1.${domain}.
ns1 IN  A   127.0.0.1
EOF
}

create_zone() {
  local domain="$1"
  validate_domain "$domain"

  mysql_exec "$PDNS_DB" <<SQL
INSERT INTO domains (name, type) VALUES ('${domain}', 'NATIVE')
  ON DUPLICATE KEY UPDATE name=name;
SQL

  local domain_id
  domain_id="$(mysql_exec -N -e "SELECT id FROM ${PDNS_DB}.domains WHERE name='${domain}' LIMIT 1;")"

  mysql_exec "$PDNS_DB" <<SQL
INSERT INTO records (domain_id, name, type, content, ttl, prio, disabled, auth)
VALUES
(${domain_id}, '${domain}', 'SOA', 'ns1.${domain} hostmaster.${domain} 1 10800 3600 604800 3600', 3600, NULL, 0, 1),
(${domain_id}, '${domain}', 'NS', 'ns1.${domain}', 3600, NULL, 0, 1)
ON DUPLICATE KEY UPDATE name=name;
SQL

  ensure_zone_file "$domain"
  systemctl reload pdns || systemctl restart pdns
  echo "Zone created: ${domain}"
}

add_record() {
  local domain="$1"
  local name="$2"
  local type="$3"
  local content="$4"
  local ttl="${5:-3600}"
  local prio="${6:-NULL}"

  validate_domain "$domain"
  type="$(echo "$type" | tr '[:lower:]' '[:upper:]')"

  local fqdn
  if [[ "$name" == "@" ]]; then
    fqdn="$domain"
  elif [[ "$name" == *"."* ]]; then
    fqdn="$name"
  else
    fqdn="${name}.${domain}"
  fi

  local domain_id
  domain_id="$(mysql_exec -N -e "SELECT id FROM ${PDNS_DB}.domains WHERE name='${domain}' LIMIT 1;")"
  [[ -n "$domain_id" ]] || { echo "Zone not found: ${domain}" >&2; exit 1; }

  mysql_exec "$PDNS_DB" <<SQL
INSERT INTO records (domain_id, name, type, content, ttl, prio, disabled, auth)
VALUES (${domain_id}, '${fqdn}', '${type}', '${content}', ${ttl}, ${prio}, 0, 1);
SQL

  systemctl reload pdns || systemctl restart pdns
  echo "Record added: ${fqdn} ${type} ${content}"
}

main() {
  require_root
  local cmd="${1:-}"
  case "$cmd" in
    create-zone)
      [[ $# -eq 2 ]] || { usage; exit 1; }
      create_zone "$2"
      ;;
    add-record)
      [[ $# -ge 6 || $# -ge 5 ]] || { usage; exit 1; }
      add_record "$2" "$3" "$4" "$5" "${6:-3600}" "${7:-NULL}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
