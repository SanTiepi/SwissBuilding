#!/bin/bash
# SwissBuilding OS — PostgreSQL Backup Script
# Usage: ./backup.sh (run via cron: 0 2 * * * /path/to/backup.sh)

set -euo pipefail

BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/swissbuildingos_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# Dump via docker exec
docker exec swissbuildingos-postgres pg_dump \
  -U "${POSTGRES_USER:-swissbuildingos}" \
  -d "${POSTGRES_DB:-swissbuildingos}" \
  --format=custom \
  --compress=9 \
  > "${BACKUP_FILE}"

# Verify backup is not empty
if [ ! -s "${BACKUP_FILE}" ]; then
  echo "ERROR: Backup file is empty!" >&2
  exit 1
fi

echo "Backup created: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"

# Cleanup old backups
find "${BACKUP_DIR}" -name "swissbuildingos_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "Cleaned up backups older than ${RETENTION_DAYS} days"
