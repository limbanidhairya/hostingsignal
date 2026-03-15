#!/usr/bin/env bash
# HS-Panel Service Installer — Snappymail (Webmail)
# Installs Snappymail (successor to Rainloop) as webmail under /webmail.

WEBMAIL_DIR="${WEBMAIL_DIR:-/var/www/hspanel/webmail}"
WEBMAIL_ALIAS="${WEBMAIL_ALIAS:-/webmail}"
SNAPPYMAIL_VERSION="${SNAPPYMAIL_VERSION:-2.36.4}"

install_rainloop() {
  log_info "Installing Snappymail (webmail) ..."

  if [[ -d "$WEBMAIL_DIR" ]]; then
    log_info "Webmail already present — skipping"
    mark_service_skipped "rainloop"
    return 0
  fi

  mkdir -p "$WEBMAIL_DIR"

  local archive="/tmp/snappymail.zip"
  local download_url="https://github.com/the-djmaze/snappymail/releases/download/v${SNAPPYMAIL_VERSION}/snappymail-${SNAPPYMAIL_VERSION}.zip"

  log_info "  Downloading Snappymail ${SNAPPYMAIL_VERSION}..."
  if ! curl -fsSL "$download_url" -o "$archive" 2>/dev/null; then
    # Fallback to latest release
    download_url="https://snappymail.eu/repository/latest.tar.gz"
    curl -fsSL "$download_url" -o "$archive" || {
      log_warning "Snappymail download failed — skipping webmail"
      mark_service_skipped "rainloop"
      return 0
    }
  fi

  if file "$archive" 2>/dev/null | grep -q "Zip"; then
    unzip -q "$archive" -d "$WEBMAIL_DIR"
  else
    tar -xzf "$archive" -C "$WEBMAIL_DIR" --strip-components=1 2>/dev/null || \
      tar -xzf "$archive" -C "$WEBMAIL_DIR" 2>/dev/null
  fi

  rm -f "$archive"

  # Set permissions
  chown -R www-data:www-data "$WEBMAIL_DIR" 2>/dev/null || \
    chown -R apache:apache "$WEBMAIL_DIR" 2>/dev/null || true
  chmod -R 755 "$WEBMAIL_DIR"

  # OLS alias
  _configure_webmail_ols_alias

  log_success "Webmail installed at: http://SERVER_IP${WEBMAIL_ALIAS}"
  mark_service_done "rainloop"
  rollback_remove_dir "$WEBMAIL_DIR"
}

_configure_webmail_ols_alias() {
  local conf_dir="/usr/local/lsws/conf"
  [[ -d "$conf_dir" ]] || return 0
  cat > "${conf_dir}/webmail.conf" <<CONF
context /webmail {
  location ${WEBMAIL_DIR}
  allowBrowse 1
  rewrite {
    enable 1
    autoLoadHtaccess 1
  }
}
CONF
}
