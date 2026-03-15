#!/usr/bin/env bash
# HS-Panel Service Installer — phpMyAdmin
# Downloads, installs, and configures phpMyAdmin under /phpmyadmin.

PHPMYADMIN_VERSION="${PHPMYADMIN_VERSION:-5.2.1}"
PHPMYADMIN_DIR="${PHPMYADMIN_DIR:-/usr/share/phpmyadmin}"
PHPMYADMIN_ALIAS="${PHPMYADMIN_ALIAS:-/phpmyadmin}"
PHPMYADMIN_BLOWFISH_SECRET=""  # auto-generated

install_phpmyadmin() {
  log_info "Installing phpMyAdmin $PHPMYADMIN_VERSION..."

  if [[ -d "$PHPMYADMIN_DIR" ]]; then
    log_info "phpMyAdmin already present — skipping"
    mark_service_skipped "phpmyadmin"
    return 0
  fi

  # Generate blowfish secret
  PHPMYADMIN_BLOWFISH_SECRET="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' | head -c 32)"

  mkdir -p "$PHPMYADMIN_DIR"
  local archive="/tmp/phpmyadmin.tar.gz"
  local download_url="https://files.phpmyadmin.net/phpMyAdmin/${PHPMYADMIN_VERSION}/phpMyAdmin-${PHPMYADMIN_VERSION}-all-languages.tar.gz"

  log_info "  Downloading phpMyAdmin..."
  curl -fsSL "$download_url" -o "$archive"

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  tar -xzf "$archive" -C "$tmp_dir" --strip-components=1
  mv "$tmp_dir/"* "$PHPMYADMIN_DIR/"
  rm -rf "$tmp_dir" "$archive"

  # Configure
  mkdir -p "${PHPMYADMIN_DIR}/tmp"
  chmod 700 "${PHPMYADMIN_DIR}/tmp"

  cp "${PHPMYADMIN_DIR}/config.sample.inc.php" "${PHPMYADMIN_DIR}/config.inc.php"

  sed -i "s|\$cfg\['blowfish_secret'\] = ''|\$cfg['blowfish_secret'] = '${PHPMYADMIN_BLOWFISH_SECRET}'|" \
    "${PHPMYADMIN_DIR}/config.inc.php"

  # Add db credentials
  cat >> "${PHPMYADMIN_DIR}/config.inc.php" <<PHP

// HS-Panel auto-configuration
\$cfg['Servers'][\$i]['host']     = 'localhost';
\$cfg['Servers'][\$i]['user']     = '${MARIADB_APP_USER}';
\$cfg['Servers'][\$i]['password'] = '${MARIADB_APP_PASSWD}';
\$cfg['TempDir']                  = '${PHPMYADMIN_DIR}/tmp';
PHP

  # OLS vhost alias for /phpmyadmin
  _configure_phpmyadmin_ols_alias
  _configure_phpmyadmin_nginx_compat

  log_success "phpMyAdmin installed at: http://SERVER_IP${PHPMYADMIN_ALIAS}"
  mark_service_done "phpmyadmin"
  rollback_remove_dir "$PHPMYADMIN_DIR"
}

_configure_phpmyadmin_ols_alias() {
  local conf_dir="/usr/local/lsws/conf"
  [[ -d "$conf_dir" ]] || return 0
  cat > "${conf_dir}/phpmyadmin.conf" <<'CONF'
# phpMyAdmin OLS alias
context /phpmyadmin {
  location /usr/share/phpmyadmin
  allowBrowse 1
  rewrite {
    enable 1
    autoLoadHtaccess 1
  }
  phpIniOverride {
  }
}
CONF
}

_configure_phpmyadmin_nginx_compat() {
  local nginx_conf="/etc/nginx/conf.d/phpmyadmin.conf"
  [[ -d "$(dirname $nginx_conf)" ]] || return 0
  cat > "$nginx_conf" <<CONF
location /phpmyadmin {
  root /usr/share;
  index index.php;
  location ~ ^/phpmyadmin/(.+\.php)$ {
    try_files \$uri =404;
    fastcgi_pass unix:/var/run/php/php8.2-fpm.sock;
    fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
    include fastcgi_params;
  }
}
CONF
}
