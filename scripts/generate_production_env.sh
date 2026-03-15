#!/usr/bin/env bash
set -euo pipefail

# Generates a hardened HSDEV environment file for launch preparation.
# Usage:
#   ./scripts/generate_production_env.sh [output_file]

OUT_FILE="${1:-deployment/hostingsignal-devapi.production.env}"

require_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		echo "Missing required command: $1" >&2
		exit 1
	fi
}

require_cmd openssl

rand_hex() {
	local bytes="$1"
	openssl rand -hex "$bytes"
}

rand_password() {
	# 32 chars with URL-safe base64 output.
	openssl rand -base64 32 | tr -d '\n' | tr '+/' '-_' | cut -c1-32
}

JWT_SECRET="$(rand_hex 32)"
DEFAULT_ADMIN_PASSWORD="$(rand_password)"
WHMCS_SHARED_SECRET="$(rand_hex 24)"
WHMCS_HMAC_SECRET="$(rand_hex 32)"

mkdir -p "$(dirname "$OUT_FILE")"

cat >"$OUT_FILE" <<EOF
# HostingSignal Developer API - Production Launch Environment
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
#
# Apply this file in your hostingsignal-devapi service unit using:
#   EnvironmentFile=/absolute/path/to/this-file

HSDEV_DEBUG=false
HSDEV_PRODUCTION_MODE=true

# Required: replace the DB host/password placeholders before launch.
HSDEV_DATABASE_URL=postgresql+asyncpg://hostingsignal:CHANGE_DB_PASSWORD@127.0.0.1:5432/hostingsignal_devpanel

# Seeded admin bootstrap (rotate post-first-login if policy requires)
HSDEV_DEFAULT_ADMIN_EMAIL=admin@hostingsignal.local
HSDEV_DEFAULT_ADMIN_USERNAME=admin
HSDEV_DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD}

# JWT/Auth
HSDEV_JWT_SECRET=${JWT_SECRET}

# Redis
HSDEV_REDIS_URL=redis://127.0.0.1:6379/2

# WHMCS integration hardening
HSDEV_WHMCS_SHARED_SECRET=${WHMCS_SHARED_SECRET}
HSDEV_WHMCS_HMAC_SECRET=${WHMCS_HMAC_SECRET}
HSDEV_WHMCS_HMAC_MAX_SKEW_SECONDS=300
HSDEV_WHMCS_NONCE_TTL_SECONDS=600
# Required: set your real WHMCS egress IPs/CIDRs
HSDEV_WHMCS_ALLOWED_IPS=203.0.113.10/32,198.51.100.20/32

# License runtime
HSDEV_LICENSE_SERVER_URL=https://license.hostingsignal.com
# Required when protected validation path enforces API key
HSDEV_LICENSE_API_KEY=CHANGE_LICENSE_API_KEY
HSDEV_LICENSE_VALIDATE_PATH=/license/validate
HSDEV_LICENSE_CACHE_PATH=/usr/local/hspanel/configs/license.cache
HSDEV_LICENSE_GRACE_HOURS=72
EOF

chmod 600 "$OUT_FILE"

echo "Generated production environment file: $OUT_FILE"
echo "Bootstrap admin password: $DEFAULT_ADMIN_PASSWORD"
echo
echo "Next steps:"
echo "  1. Replace CHANGE_DB_PASSWORD and CHANGE_LICENSE_API_KEY in $OUT_FILE"
echo "  2. Replace HSDEV_WHMCS_ALLOWED_IPS with real callback source ranges"
echo "  3. Configure hostingsignal-devapi with EnvironmentFile=$OUT_FILE"
echo "  4. Restart service and verify /api/system/preflight"
