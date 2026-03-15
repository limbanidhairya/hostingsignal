#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

GITHUB_OWNER="${HS_REPO_OWNER:-limbanidhairya}"
GITHUB_REPO="${HS_REPO_NAME:-hostingsignal}"
GITHUB_REF="${HS_REPO_REF:-main}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 is required to run the HostingSignal installer" >&2
  exit 1
fi

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

  echo "Either curl or wget is required to bootstrap from GitHub" >&2
  return 1
}

bootstrap_repo() {
  local tmp_root archive_url archive_file extracted_root
  tmp_root="$(mktemp -d -t hostingsignal-bootstrap-XXXXXX)"

  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 --branch "$GITHUB_REF" "https://github.com/$GITHUB_OWNER/$GITHUB_REPO.git" "$tmp_root/repo" >/dev/null 2>&1 || true
    if [[ -f "$tmp_root/repo/scripts/local_installer.py" ]]; then
      echo "$tmp_root/repo"
      return 0
    fi
  fi

  archive_url="https://github.com/$GITHUB_OWNER/$GITHUB_REPO/archive/$GITHUB_REF.tar.gz"
  archive_file="$tmp_root/repo.tar.gz"
  download_file "$archive_url" "$archive_file"

  tar -xzf "$archive_file" -C "$tmp_root"
  extracted_root="$(find "$tmp_root" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

  if [[ -z "$extracted_root" || ! -f "$extracted_root/scripts/local_installer.py" ]]; then
    echo "Unable to locate scripts/local_installer.py after bootstrap" >&2
    exit 1
  fi

  echo "$extracted_root"
}

resolve_root_dir() {
  if [[ -f "$SCRIPT_DIR/scripts/local_installer.py" ]]; then
    echo "$SCRIPT_DIR"
    return 0
  fi
  bootstrap_repo
}

ROOT_DIR="$(resolve_root_dir)"

if [[ "$#" -eq 0 ]]; then
  set -- --mode all --all --non-interactive --web openlitespeed --db mariadb
fi

echo "Starting HostingSignal installer from: $ROOT_DIR"
exec "$PYTHON_BIN" "$ROOT_DIR/scripts/local_installer.py" "$@"
