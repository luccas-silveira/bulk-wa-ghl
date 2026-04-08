#!/bin/bash
###############################################################################
# Database Backup Script
# Creates a PostgreSQL backup with timestamp
# Usage: ./scripts/backup-db.sh
###############################################################################

set -e  # Exit on error

# Configuration
BACKUP_DIR="/var/backups/wpp-disp/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="wpp_disp_backup_${DATE}.sql.gz"

# Load environment variables safely
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "📦 Starting database backup..."
echo "Backup file: ${BACKUP_FILE}"

# Create backup using docker exec
docker exec wpp_disp_postgres pg_dump \
    -U "${POSTGRES_USER:-wpp_disp}" \
    -d "${POSTGRES_DB:-wpp_disp_db}" \
    -F plain \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "✅ Backup completed successfully!"
    echo "Location: ${BACKUP_DIR}/${BACKUP_FILE}"

    # Show backup size
    SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo "Size: ${SIZE}"

    # Keep only last 7 daily backups
    echo "🧹 Cleaning up old backups (keeping last 7)..."
    cd "$BACKUP_DIR"
    ls -t wpp_disp_backup_*.sql.gz | tail -n +8 | xargs -r rm --

    echo "📊 Available backups:"
    ls -lh wpp_disp_backup_*.sql.gz 2>/dev/null | tail -7
else
    echo "❌ Backup failed!"
    exit 1
fi
