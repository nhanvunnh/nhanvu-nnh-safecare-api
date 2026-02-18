#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"
ENV_FILE="${INFRA_DIR}/.env.infra"
BACKUP_ROOT=${BACKUP_ROOT:-/opt/backups/mongo}
RETENTION_COUNT=${RETENTION_COUNT:-7}
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_PATH="${BACKUP_ROOT}/mongo-${TIMESTAMP}.archive.gz"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

mkdir -p "${BACKUP_ROOT}"

echo "Starting MongoDB backup to ${ARCHIVE_PATH}"
docker exec shared_mongo mongodump \
  --username "${MONGO_ROOT_USER}" \
  --password "${MONGO_ROOT_PASS}" \
  --authenticationDatabase admin \
  --gzip \
  --archive - > "${ARCHIVE_PATH}"

echo "Backup created. Applying retention (keeping ${RETENTION_COUNT})..."
mapfile -t backups < <(ls -1t "${BACKUP_ROOT}"/mongo-*.archive.gz 2>/dev/null || true)
if (( ${#backups[@]} > RETENTION_COUNT )); then
  for old_backup in "${backups[@]:${RETENTION_COUNT}}"; do
    rm -f "${old_backup}"
    echo "Removed ${old_backup}"
  done
fi

echo "MongoDB backup finished."
