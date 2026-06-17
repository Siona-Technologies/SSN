#!/usr/bin/env bash
# Backup SIONA runtime state (SSN_STATE_DIR) to a compressed archive.
#
# Usage:
#   ./scripts/backup_state.sh
#   ./scripts/backup_state.sh /path/to/backup.tar.gz
#   SSN_STATE_DIR=/var/lib/siona/state ./scripts/backup_state.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${SSN_STATE_DIR:-${ROOT}/.ssn_state}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT="${1:-${ROOT}/backups/siona-state-${TIMESTAMP}.tar.gz}"

if [[ ! -d "${STATE_DIR}" ]]; then
  echo "ERROR: state dir not found: ${STATE_DIR}" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUT}")"
PARENT="$(cd "$(dirname "${STATE_DIR}")" && pwd)"
BASE="$(basename "${STATE_DIR}")"

tar -czf "${OUT}" -C "${PARENT}" "${BASE}"
echo "Backup written: ${OUT}"
echo "Restore: tar -xzf ${OUT} -C ${PARENT}"
