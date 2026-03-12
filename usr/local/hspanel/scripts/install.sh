#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
CANONICAL_INSTALLER="${REPO_ROOT}/install.sh"

if [[ ! -f "${CANONICAL_INSTALLER}" ]]; then
  echo "Canonical installer not found at ${CANONICAL_INSTALLER}"
  exit 1
fi

echo "Delegating to ${CANONICAL_INSTALLER}"
exec bash "${CANONICAL_INSTALLER}" "$@"
