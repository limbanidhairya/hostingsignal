#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 is required to run the HostingSignal local installer" >&2
  exit 1
fi

exec "${PYTHON_BIN}" "${ROOT_DIR}/scripts/local_installer.py" "$@"
