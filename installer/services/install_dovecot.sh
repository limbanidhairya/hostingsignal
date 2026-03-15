#!/usr/bin/env bash
# HS-Panel Service Installer — Dovecot (IMAP/POP3)
# Installs and configures Dovecot with Maildir storage + SASL for Postfix.

install_dovecot() {
  log_info "Installing Dovecot..."

  if systemctl is-active --quiet dovecot 2>/dev/null; then
    log_info "Dovecot already running — skipping"
    mark_service_skipped "dovecot"
    return 0
  fi

  if [[ "$OS_FAMILY" == "debian" ]]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-sieve
  else
    dnf install -y dovecot dovecot-mysql --skip-broken
  fi

  _configure_dovecot
  systemctl enable --now dovecot

  log_success "Dovecot installed (IMAP/POP3 + SASL)"
  mark_service_done "dovecot"
  rollback_stop_service "dovecot"
}

_configure_dovecot() {
  local conf_dir="/etc/dovecot"

  # Protocols
  sed -i 's|^#protocols.*|protocols = imap pop3 lmtp|' "${conf_dir}/dovecot.conf" 2>/dev/null || \
    echo "protocols = imap pop3 lmtp" >> "${conf_dir}/dovecot.conf"

  # Mail location (Maildir)
  sed -i 's|^#mail_location.*|mail_location = maildir:~/Maildir|' "${conf_dir}/conf.d/10-mail.conf" 2>/dev/null || true

  # Authentication (plain + login for SASL compatibility with Postfix)
  cat > "${conf_dir}/conf.d/10-auth.conf" <<'EOF'
disable_plaintext_auth = no
auth_mechanisms = plain login

!include auth-system.conf.ext
EOF

  # SASL socket for Postfix
  cat > "${conf_dir}/conf.d/10-master.conf" <<'EOF'
service imap-login {
  inet_listener imap  { port = 143 }
  inet_listener imaps { port = 993  ssl = yes }
}
service pop3-login {
  inet_listener pop3  { port = 110 }
  inet_listener pop3s { port = 995  ssl = yes }
}
service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}
service auth {
  unix_listener auth-userdb {}
  unix_listener /var/spool/postfix/private/auth {
    mode = 0666
    user = postfix
    group = postfix
  }
}
service auth-worker { user = root }
EOF

  # SSL — use snakeoil if available
  local ssl_conf="${conf_dir}/conf.d/10-ssl.conf"
  if [[ -f /etc/ssl/certs/ssl-cert-snakeoil.pem ]]; then
    cat > "$ssl_conf" <<'EOF'
ssl = yes
ssl_cert = </etc/ssl/certs/ssl-cert-snakeoil.pem
ssl_key  = </etc/ssl/private/ssl-cert-snakeoil.key
EOF
  else
    cat > "$ssl_conf" <<'EOF'
ssl = no
EOF
  fi

  log_info "Dovecot configured (Maildir, IMAP 143/993, POP3 110/995)"
}
