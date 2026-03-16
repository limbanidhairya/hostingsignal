#!/usr/bin/env bash
set -euo pipefail

PREFIX="[HostingSignal]"
REPO_OWNER="${HS_REPO_OWNER:-limbanidhairya}"
REPO_NAME="${HS_REPO_NAME:-hostingsignal}"
REPO_REF="${HS_REPO_REF:-main}"

log() {
  echo "${PREFIX} $*"
}

fail() {
  echo "${PREFIX} ERROR: $*" >&2
  exit 1
}

download_file() {
  local url="$1"
  local out="$2"

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$out"
    return 0
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -qO "$out" "$url"
    return 0
  fi

  fail "curl or wget is required"
}

bootstrap_repo() {
  local tmp_root archive_url archive_file extracted_root
  tmp_root="$(mktemp -d -t hostingsignal-bootstrap-XXXXXX)"

  if command -v git >/dev/null 2>&1; then
    if git clone --depth 1 --branch "$REPO_REF" "https://github.com/$REPO_OWNER/$REPO_NAME.git" "$tmp_root/repo" >/dev/null 2>&1; then
      if [[ -f "$tmp_root/repo/installer/install.sh" ]]; then
        echo "$tmp_root/repo"
        return 0
      fi
    fi
  fi

  archive_url="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/${REPO_REF}.tar.gz"
  archive_file="$tmp_root/repo.tar.gz"
  download_file "$archive_url" "$archive_file"

  tar -xzf "$archive_file" -C "$tmp_root"
  extracted_root="$(find "$tmp_root" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

  [[ -n "$extracted_root" ]] || fail "Unable to extract repository archive"
  [[ -f "$extracted_root/installer/install.sh" ]] || fail "installer/install.sh not found in repository"

  echo "$extracted_root"
}

main() {
  [[ "$(id -u)" -eq 0 ]] || fail "Run with sudo or as root"

  log "Bootstrapping HS-Panel native installer from GitHub"
  local root_dir
  root_dir="$(bootstrap_repo)"

  log "Running native installer"
  exec bash "$root_dir/installer/install.sh" "$@"
}

main "$@"
