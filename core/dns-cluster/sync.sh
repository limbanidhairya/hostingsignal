#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CFG_FILE="${ROOT_DIR}/configs/dns-cluster.yaml"

if [[ ! -f "${CFG_FILE}" ]]; then
  echo "dns cluster config missing: ${CFG_FILE}" >&2
  exit 1
fi

master_ip="$(awk '/^master:/{found=1;next} found && /ip:/{print $2; exit}' "${CFG_FILE}")"
mapfile -t slave_ips < <(awk '/^slaves:/{found=1;next} found && /^\s*-/{gsub("- ","",$0); gsub(/^\s+|\s+$/, "", $0); print $0} /^sync:/{found=0}' "${CFG_FILE}")

cmd="${1:-status}"
zone="${2:-example.com}"

soa_serial() {
  local host_ip="$1"
  local domain="$2"
  if ! command -v dig >/dev/null 2>&1; then
    echo ""
    return 1
  fi
  # SOA format: primary-ns hostmaster serial refresh retry expire minimum
  dig +time=2 +tries=1 +short SOA "${domain}" @"${host_ip}" 2>/dev/null | awk 'NR==1{print $3}'
}

case "${cmd}" in
  status)
    echo "master=${master_ip}"
    echo "slaves=${#slave_ips[@]}"
    for ip in "${slave_ips[@]}"; do
      echo "slave=${ip}"
    done
    ;;
  sync)
    echo "sync-trigger zone=${zone} master=${master_ip}"
    for ip in "${slave_ips[@]}"; do
      echo "verify-slave ${ip}"
      if command -v dig >/dev/null 2>&1; then
        if dig +short "${zone}" @"${ip}" >/dev/null 2>&1; then
          echo "ok ${ip}"
        else
          echo "warn ${ip} no response for ${zone}"
        fi
      else
        echo "warn dig not installed; skipped check for ${ip}"
      fi
    done
    ;;
  verify)
    if ! command -v dig >/dev/null 2>&1; then
      echo "dig is required for replication checks" >&2
      exit 2
    fi

    master_serial="$(soa_serial "${master_ip}" "${zone}")"
    if [[ -z "${master_serial}" ]]; then
      echo "failed to query master SOA serial for zone=${zone} @${master_ip}" >&2
      exit 1
    fi

    echo "verify zone=${zone} master=${master_ip} serial=${master_serial}"
    failed=0
    for ip in "${slave_ips[@]}"; do
      slave_serial="$(soa_serial "${ip}" "${zone}")"
      if [[ -z "${slave_serial}" ]]; then
        echo "fail ${ip} no SOA response"
        failed=$((failed + 1))
        continue
      fi
      if [[ "${slave_serial}" == "${master_serial}" ]]; then
        echo "ok ${ip} serial=${slave_serial}"
      else
        echo "drift ${ip} serial=${slave_serial} expected=${master_serial}"
        failed=$((failed + 1))
      fi
    done

    if [[ ${failed} -gt 0 ]]; then
      echo "replication-check failed count=${failed}" >&2
      exit 1
    fi
    echo "replication-check healthy"
    ;;
  *)
    echo "usage: $0 [status|sync|verify] [zone]" >&2
    exit 2
    ;;
esac
