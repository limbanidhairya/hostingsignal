#!/usr/bin/env bash
# HS-Panel Installer — Service Orchestrator
# Defines the dependency graph and resolves install order.

# ── Dependency graph ──────────────────────────────────────────────────────────
# Each entry: "SERVICE:dep1,dep2,..."
# Empty dependencies mean no prereqs.

declare -A SERVICE_DEPS=(
  ["system"]=""
  ["openlitespeed"]="system"
  ["mariadb"]="system"
  ["php"]="openlitespeed"
  ["phpmyadmin"]="mariadb,openlitespeed"
  ["postfix"]="system"
  ["dovecot"]="postfix"
  ["rainloop"]="dovecot,openlitespeed"
  ["powerdns"]="mariadb"
  ["hspanel"]="mariadb,openlitespeed,php"
)

# Resolved install order (populated by resolve_order)
declare -a INSTALL_ORDER=()

# Track visited/resolved state for topological sort
declare -A _VISITED=()
declare -A _IN_STACK=()

_resolve_service() {
  local svc="$1"

  if [[ -n "${_IN_STACK[$svc]:-}" ]]; then
    log_error "Circular dependency detected for service: $svc" >&2
    exit 1
  fi

  [[ -n "${_VISITED[$svc]:-}" ]] && return 0

  _IN_STACK["$svc"]=1

  local deps="${SERVICE_DEPS[$svc]:-}"
  if [[ -n "$deps" ]]; then
    IFS=',' read -ra dep_list <<< "$deps"
    for dep in "${dep_list[@]}"; do
      dep="$(echo "$dep" | tr -d ' ')"
      _resolve_service "$dep"
    done
  fi

  unset '_IN_STACK[$svc]'
  _VISITED["$svc"]=1
  INSTALL_ORDER+=("$svc")
}

resolve_order() {
  INSTALL_ORDER=()
  _VISITED=()
  _IN_STACK=()

  for svc in "${!SERVICE_DEPS[@]}"; do
    _resolve_service "$svc"
  done
}

print_install_order() {
  log_info "Resolved install order:"
  local i=1
  for svc in "${INSTALL_ORDER[@]}"; do
    log_kv "  Step $i" "$svc"
    (( i++ ))
  done
}

# ── Service state tracking ────────────────────────────────────────────────────
declare -A SERVICE_STATUS=()

mark_service_done() {
  local svc="$1"
  SERVICE_STATUS["$svc"]="done"
  record_installed "$svc" 2>/dev/null || true
}

mark_service_skipped() {
  local svc="$1"
  SERVICE_STATUS["$svc"]="skipped"
}

mark_service_failed() {
  local svc="$1"
  SERVICE_STATUS["$svc"]="failed"
}

# ── Dependency check ──────────────────────────────────────────────────────────
deps_satisfied() {
  local svc="$1"
  local deps="${SERVICE_DEPS[$svc]:-}"

  [[ -z "$deps" ]] && return 0

  IFS=',' read -ra dep_list <<< "$deps"
  for dep in "${dep_list[@]}"; do
    dep="$(echo "$dep" | tr -d ' ')"
    local state="${SERVICE_STATUS[$dep]:-}"
    if [[ "$state" != "done" && "$state" != "skipped" ]]; then
      log_warning "Dependency '$dep' not satisfied for '$svc' (state: ${state:-not run})"
      return 1
    fi
  done
  return 0
}

# ── Print dependency diagram (ASCII) ─────────────────────────────────────────
print_dependency_graph() {
  echo ""
  echo -e "  ${C_BOLD}${C_CYAN}Dependency Graph${C_RESET}"
  echo ""
  echo "  system"
  echo "  ├── openlitespeed"
  echo "  │   └── php"
  echo "  │       ├── phpmyadmin  (also needs: mariadb)"
  echo "  │       └── hspanel    (also needs: mariadb)"
  echo "  ├── mariadb"
  echo "  │   ├── phpmyadmin"
  echo "  │   ├── powerdns"
  echo "  │   └── hspanel"
  echo "  ├── postfix"
  echo "  │   └── dovecot"
  echo "  │       └── rainloop   (also needs: openlitespeed)"
  echo "  └── powerdns"
  echo ""
}
