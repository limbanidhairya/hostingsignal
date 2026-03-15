#!/usr/bin/env bash
# HS-Panel Service Installer — Postfix (SMTP)
# Installs and configures Postfix for outbound and inbound mail.

MAIL_HOSTNAME="${MAIL_HOSTNAME:-$(hostname -f 2>/dev/null || hostname)}"
MAIL_DOMAIN="${MAIL_DOMAIN:-$(hostname -d 2>/dev/null || echo 'localdomain')}"

install_postfix() {
  log_info "Installing Postfix..."

  if systemctl is-active --quiet postfix 2>/dev/null; then
    log_info "Postfix already running — skipping"
    mark_service_skipped "postfix"
    return 0
  fi

  if [[ "$OS_FAMILY" == "debian" ]]; then
    # Pre-seed debconf to avoid interactive prompts
    debconf-set-selections <<< "postfix postfix/mailname string ${MAIL_HOSTNAME}"
    debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postfix postfix-mysql mailutils
  else
    dnf install -y postfix postfix-mysql mailx --skip-broken
  fi

  _configure_postfix
  systemctl enable --now postfix

  log_success "Postfix installed (hostname: $MAIL_HOSTNAME)"
  mark_service_done "postfix"
  rollback_stop_service "postfix"
}

_configure_postfix() {
  local cf="/etc/postfix/main.cf"

  # Backup original
  [[ -f "${cf}.orig" ]] || cp "$cf" "${cf}.orig"

  # Core settings
  postconf -e "myhostname = ${MAIL_HOSTNAME}"
  postconf -e "mydomain = ${MAIL_DOMAIN}"
  postconf -e "myorigin = \$mydomain"
  postconf -e "inet_interfaces = all"
  postconf -e "inet_protocols = ipv4"
  postconf -e "mydestination = \$myhostname, localhost.\$mydomain, localhost, \$mydomain"
  postconf -e "mynetworks = 127.0.0.0/8"
  postconf -e "home_mailbox = Maildir/"
  postconf -e "smtpd_banner = \$myhostname ESMTP HostingSignal"

  # TLS settings (self-signed for now)
  if [[ -f /etc/ssl/certs/ssl-cert-snakeoil.pem ]]; then
    postconf -e "smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem"
    postconf -e "smtpd_tls_key_file = /etc/ssl/private/ssl-cert-snakeoil.key"
  fi
  postconf -e "smtpd_tls_security_level = may"
  postconf -e "smtp_tls_security_level = may"
  postconf -e "smtpd_tls_loglevel = 1"

  # SASL
  postconf -e "smtpd_sasl_type = dovecot"
  postconf -e "smtpd_sasl_path = private/auth"
  postconf -e "smtpd_sasl_auth_enable = yes"
  postconf -e "smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination"

  # Enable submission (587) and smtps (465)
  local master="/etc/postfix/master.cf"
  if ! grep -q "^submission " "$master" 2>/dev/null; then
    cat >> "$master" <<'EOF'
submission inet n - y - - smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject

smtps     inet  n       -       y       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
EOF
  fi

  log_info "Postfix configured (domain: $MAIL_DOMAIN)"
}
