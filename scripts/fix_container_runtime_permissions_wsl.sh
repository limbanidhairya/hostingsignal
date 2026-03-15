#!/usr/bin/env bash
set -euo pipefail

# Repairs common Docker runtime permission issues in WSL.
#
# Usage:
#   sudo bash scripts/fix_container_runtime_permissions_wsl.sh [username]

TARGET_USER="${1:-${SUDO_USER:-${USER:-}}}"
if [[ -z "${TARGET_USER}" ]]; then
  echo "Unable to determine target user. Pass username explicitly." >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (use sudo)." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found; install Docker first." >&2
  exit 1
fi

echo "==> Ensuring docker group exists"
getent group docker >/dev/null 2>&1 || groupadd docker

echo "==> Adding ${TARGET_USER} to docker group"
usermod -aG docker "${TARGET_USER}"

echo "==> Restarting docker service if present"
if systemctl list-unit-files | grep -q '^docker.service'; then
  systemctl restart docker || true
fi

echo "==> Verifying runtime access as ${TARGET_USER}"
if su - "${TARGET_USER}" -c 'docker info >/dev/null 2>&1'; then
  echo "docker runtime accessible for ${TARGET_USER}"
else
  echo "docker runtime still not accessible for ${TARGET_USER}" >&2
  echo "Log out/in or restart WSL session, then re-test: docker info" >&2
  exit 1
fi

echo "Permission fix complete"
