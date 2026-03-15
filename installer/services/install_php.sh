#!/usr/bin/env bash
# HS-Panel Service Installer — PHP (multi-version)
# Installs PHP 8.1, 8.2, 8.3 with common extensions for OLS/Apache.

PHP_VERSIONS="${PHP_VERSIONS:-8.1 8.2 8.3}"
PHP_DEFAULT="${PHP_DEFAULT:-8.2}"

install_php() {
  log_info "Installing PHP (versions: $PHP_VERSIONS)..."

  if [[ "$OS_FAMILY" == "debian" ]]; then
    _setup_php_repo_debian
    for ver in $PHP_VERSIONS; do
      _install_php_debian "$ver"
    done
  else
    _setup_php_repo_rhel
    for ver in $PHP_VERSIONS; do
      _install_php_rhel "$ver"
    done
  fi

  # Set default CLI php
  if command -v update-alternatives &>/dev/null; then
    update-alternatives --set php "/usr/bin/php${PHP_DEFAULT}" 2>/dev/null || true
  fi

  log_success "PHP installed (default: $PHP_DEFAULT)"
  mark_service_done "php"
}

_setup_php_repo_debian() {
  if [[ ! -f /etc/apt/sources.list.d/php.list ]]; then
    add-apt-repository -y ppa:ondrej/php > /dev/null 2>&1 || \
      curl -fsSL https://packages.sury.org/php/README.txt | bash > /dev/null 2>&1 || true
    apt-get update -qq
  fi
}

_install_php_debian() {
  local ver="$1"
  local extensions=(
    "php${ver}" "php${ver}-fpm" "php${ver}-cli"
    "php${ver}-common" "php${ver}-mysql" "php${ver}-pgsql"
    "php${ver}-curl" "php${ver}-gd" "php${ver}-mbstring"
    "php${ver}-xml" "php${ver}-zip" "php${ver}-bcmath"
    "php${ver}-intl" "php${ver}-readline" "php${ver}-soap"
    "php${ver}-redis" "php${ver}-memcached" "php${ver}-opcache"
    "php${ver}-imagick" "php${ver}-apcu"
  )
  log_info "  Installing PHP $ver..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${extensions[@]}" 2>/dev/null || \
    log_warning "Some PHP $ver extensions could not be installed"

  systemctl enable --now "php${ver}-fpm" 2>/dev/null || true
}

_setup_php_repo_rhel() {
  dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E '%{rhel}').noarch.rpm 2>/dev/null || true
  dnf install -y https://rpms.remirepo.net/enterprise/remi-release-$(rpm -E '%{rhel}').rpm 2>/dev/null || true
}

_install_php_rhel() {
  local ver="$1"
  local ver_nodot="${ver//./}"  # 8.2 → 82

  dnf module reset   -y "php:remi-${ver}" 2>/dev/null || true
  dnf module enable  -y "php:remi-${ver}" 2>/dev/null || true

  local extensions=(
    "php${ver_nodot}" "php${ver_nodot}-php-fpm" "php${ver_nodot}-php-cli"
    "php${ver_nodot}-php-common" "php${ver_nodot}-php-mysqlnd"
    "php${ver_nodot}-php-curl" "php${ver_nodot}-php-gd"
    "php${ver_nodot}-php-mbstring" "php${ver_nodot}-php-xml"
    "php${ver_nodot}-php-zip" "php${ver_nodot}-php-bcmath"
    "php${ver_nodot}-php-opcache"
  )

  log_info "  Installing PHP $ver..."
  dnf install -y "${extensions[@]}" --skip-broken 2>/dev/null || \
    log_warning "Some PHP $ver extensions could not be installed"

  systemctl enable --now "php${ver_nodot}-php-fpm" 2>/dev/null || true
}
