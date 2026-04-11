#!/bin/bash
###############################################################################
# Database Backup Script
# Creates a PostgreSQL backup, verifies integrity, encrypts with AES-256-CBC,
# and retains only the last 10 backups.
# Usage: ./scripts/backup-db.sh
# Requires: BACKUP_ENCRYPTION_KEY env var (or set in .env)
###############################################################################

set -e  # Exit on error

# Configuration
BACKUP_DIR="/var/backups/wpp-disp/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
RAW_FILE="${BACKUP_DIR}/wpp_disp_backup_${DATE}.sql.gz"
ENCRYPTED_FILE="${RAW_FILE}.enc"

# Load environment variables safely
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Validate encryption key
if [ -z "${BACKUP_ENCRYPTION_KEY}" ]; then
    echo "❌ BACKUP_ENCRYPTION_KEY is not set. Export it before running this script."
    exit 1
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "📦 Starting database backup..."
echo "Backup file: wpp_disp_backup_${DATE}.sql.gz.enc"

# Step 1: Dump and compress
docker exec wpp_disp_postgres pg_dump \
    -U "${POSTGRES_USER:-wpp_disp}" \
    -d "${POSTGRES_DB:-wpp_disp_db}" \
    -F plain \
    | gzip > "${RAW_FILE}"

if [ $? -ne 0 ] || [ ! -s "${RAW_FILE}" ]; then
    echo "❌ pg_dump failed or produced an empty file!"
    rm -f "${RAW_FILE}"
    exit 1
fi

# Step 2: Verify gzip integrity before encrypting
echo "🔍 Verifying backup integrity..."
if ! gunzip -t "${RAW_FILE}" 2>/dev/null; then
    echo "❌ Backup integrity check failed (gunzip -t). File may be corrupt."
    rm -f "${RAW_FILE}"
    exit 1
fi
echo "✅ Integrity verified."

# Step 3: Encrypt with AES-256-CBC
echo "🔐 Encrypting backup..."
openssl enc -aes-256-cbc -salt -pbkdf2 \
    -pass "pass:${BACKUP_ENCRYPTION_KEY}" \
    -in "${RAW_FILE}" \
    -out "${ENCRYPTED_FILE}"

if [ $? -ne 0 ]; then
    echo "❌ Encryption failed!"
    rm -f "${RAW_FILE}" "${ENCRYPTED_FILE}"
    exit 1
fi

# Step 4: Remove unencrypted intermediate file
rm -f "${RAW_FILE}"

# Report size
SIZE=$(du -h "${ENCRYPTED_FILE}" | cut -f1)
echo "✅ Backup completed and encrypted!"
echo "Location: ${ENCRYPTED_FILE}"
echo "Size: ${SIZE}"

# Step 5: Keep only last 10 encrypted backups
echo "🧹 Cleaning up old backups (keeping last 10)..."
cd "$BACKUP_DIR"
ls -t wpp_disp_backup_*.sql.gz.enc 2>/dev/null | tail -n +11 | xargs -r rm --

echo "📊 Available backups:"
ls -lh wpp_disp_backup_*.sql.gz.enc 2>/dev/null | tail -10
