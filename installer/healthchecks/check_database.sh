#!/usr/bin/env bash
# HS-Panel Health Check — Database (MariaDB)

check_database() {
  local status=0

  # 1. systemd unit
  if systemctl is-active --quiet mariadb 2>/dev/null || systemctl is-active --quiet mysql 2>/dev/null; then
    log_success "  [database] MariaDB service active"
  else
    log_error   "  [database] MariaDB service NOT active"
    status=1
    return $status
  fi

  # 2. Port 3306
  if _port_open 3306; then
    log_success "  [database] port 3306 responding"
  else
    log_error   "  [database] port 3306 NOT responding"
    status=1
  fi

  # 3. Ping
  if mysqladmin ping --silent 2>/dev/null || \
     mysqladmin --defaults-file=/root/.my.cnf ping --silent 2>/dev/null; then
    log_success "  [database] mysqladmin ping OK"
  else
    log_error   "  [database] mysqladmin ping FAILED"
    status=1
  fi

  # 4. Database exists
  local db_check
  db_check="$(mysql --defaults-file=/root/.my.cnf -e \
    "SHOW DATABASES LIKE '${MARIADB_APP_DB:-hspanel}';" 2>/dev/null | grep -c "${MARIADB_APP_DB:-hspanel}" || echo 0)"
  if [[ "$db_check" -gt 0 ]]; then
    log_success "  [database] database '${MARIADB_APP_DB:-hspanel}' exists"
  else
    log_error   "  [database] database '${MARIADB_APP_DB:-hspanel}' NOT found"
    status=1
  fi

  # 5. App user can connect
  if mysql --user="${MARIADB_APP_USER:-hspanel_user}" \
           --password="${MARIADB_APP_PASSWD:-}" \
           --database="${MARIADB_APP_DB:-hspanel}" \
           -e "SELECT 1;" &>/dev/null; then
    log_success "  [database] app user can connect"
  else
    log_warning "  [database] app user connect test failed (check password)"
  fi

  return $status
}
