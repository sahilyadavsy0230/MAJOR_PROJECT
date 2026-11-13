#!/bin/bash
# ==============================================================================
# PRASHANT GROUP WORKFORCE PLATFORM — AUTOMATED DAILY POSTGRESQL BACKUP
# ==============================================================================
# Schedules via cron: 0 2 * * * /path/to/backup_database.sh >> /var/log/pg_backup.log 2>&1
# ==============================================================================

set -euo pipefail

# Configuration
DB_NAME="${DB_NAME:-prashant_group}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/opt/prashant_group/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql.gz"
LOG_PREFIX="[$(date +'%Y-%m-%d %H:%M:%S')]"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "${LOG_PREFIX} Starting daily database backup for ${DB_NAME}..."

# Execute pg_dump piped through gzip with maximum compression
PGPASSWORD="${PGPASSWORD:-postgres123}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -F p \
    --no-owner \
    --no-privileges \
    "${DB_NAME}" | gzip -9 > "${BACKUP_FILE}"

# Verify backup archive integrity
if gzip -t "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "${LOG_PREFIX} SUCCESS: Backup verified and saved: ${BACKUP_FILE} (Size: ${BACKUP_SIZE})"
else
    echo "${LOG_PREFIX} ERROR: Backup integrity check failed on ${BACKUP_FILE}!" >&2
    exit 1
fi

# Apply retention policy: Remove backups older than RETENTION_DAYS
echo "${LOG_PREFIX} Purging backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_backup_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -exec rm -v {} \;

echo "${LOG_PREFIX} Daily backup pipeline completed successfully."
