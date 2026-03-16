#!/usr/bin/env bash
set -euo pipefail

# Domain provisioning engine.
# Workflow:
# validate domain -> create DNS zone -> create web directory -> OLS vhost -> reload

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DNS_ENGINE="${SCRIPT_DIR}/dns_engine.sh"
SITES_ROOT="${SITES_ROOT:-/home/sites}"
USERS_ROOT="${USERS_ROOT:-/home/users}"
OLS_VHOST_ROOT="${OLS_VHOST_ROOT:-/usr/local/lsws/conf/vhosts}"
OLS_HTTPD_CONF="${OLS_HTTPD_CONF:-/usr/local/lsws/conf/httpd_config.conf}"

usage() {
  cat <<EOF
Usage:
  $0 <system_user> <domain> [ip]
Example:
  $0 user1 example.com 203.0.113.10
EOF
}

validate_domain() {
  local d="$1"
  [[ "$d" =~ ^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$ ]] || {
    echo "Invalid domain: $d" >&2
    exit 1
  }
}

ensure_user() {
  local user="$1"
  if ! id "$user" >/dev/null 2>&1; then
    useradd -m -d "${USERS_ROOT}/${user}" -s /bin/bash "$user"
  fi
}

create_site_dir() {
  local user="$1"
  local domain="$2"

  local site_dir="${USERS_ROOT}/${user}/domains/${domain}/public_html"
  mkdir -p "$site_dir"
  chown -R "$user":"$user" "${USERS_ROOT}/${user}/domains/${domain}"

  mkdir -p "${SITES_ROOT}/${domain}/public_html"
  ln -sfn "$site_dir" "${SITES_ROOT}/${domain}/public_html"

  if [[ ! -f "$site_dir/index.html" ]]; then
    cat > "$site_dir/index.html" <<EOF
<!doctype html>
<html><body><h1>${domain} is live on HS-Panel</h1></body></html>
EOF
  fi
}

create_ols_vhost() {
  local domain="$1"
  local root="${USERS_ROOT}/$(stat -c '%U' "${SITES_ROOT}/${domain}/public_html" 2>/dev/null || echo root)/domains/${domain}/public_html"

  local vhost_dir="${OLS_VHOST_ROOT}/${domain}"
  mkdir -p "$vhost_dir/logs"

  cat > "${vhost_dir}/vhconf.conf" <<EOF
docRoot                   ${root}

index  {
  useServer               0
  indexFiles              index.php,index.html
}

errorlog ${vhost_dir}/logs/error.log {
  useServer               0
  logLevel                ERROR
}

accesslog ${vhost_dir}/logs/access.log {
  useServer               0
  logFormat               "%h %l %u %t \"%r\" %>s %b"
}
EOF

  if ! grep -q "vhDomain ${domain}" "$OLS_HTTPD_CONF" 2>/dev/null; then
    cat >> "$OLS_HTTPD_CONF" <<EOF

virtualhost ${domain} {
  vhRoot                  ${vhost_dir}
  configFile              ${vhost_dir}/vhconf.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
  setUIDMode              0
  vhDomain                ${domain}
}

listener Default {
  map                     ${domain} ${domain}
  map                     www.${domain} ${domain}
}
EOF
  fi

  systemctl reload lsws || systemctl restart lsws
}

main() {
  [[ $# -ge 2 ]] || { usage; exit 1; }
  local user="$1"
  local domain="$2"
  local ip="${3:-$(hostname -I | awk '{print $1}') }"

  validate_domain "$domain"
  ensure_user "$user"
  create_site_dir "$user" "$domain"

  if [[ -x "$DNS_ENGINE" ]]; then
    "$DNS_ENGINE" create-zone "$domain"
    "$DNS_ENGINE" add-record "$domain" "@" A "$ip" 3600
    "$DNS_ENGINE" add-record "$domain" "www" CNAME "$domain" 3600
  fi

  create_ols_vhost "$domain"

  echo "Domain provisioned: ${domain}"
  echo "Site path: ${USERS_ROOT}/${user}/domains/${domain}/public_html"
  echo "SSL issuance can be enabled in a future certbot integration step."
}

main "$@"
