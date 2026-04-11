#!/bin/bash
###############################################################################
# Database Migration Script
# Runs Alembic migrations in the backend container.
# Automatically creates a backup before migrating.
# Usage: ./scripts/migrate-db.sh
###############################################################################

set -e  # Exit on error

echo "🔄 Starting migration workflow..."

# Step 1: Check if backend container is running
if ! docker ps | grep -q wpp_disp_backend; then
    echo "❌ Backend container is not running!"
    echo "Start it with: docker-compose up -d backend"
    exit 1
fi

# Step 2: Run pre-migration backup
echo "📦 Creating pre-migration backup..."
if ! ./scripts/backup-db.sh; then
    echo "❌ Pre-migration backup failed. Aborting migration to protect data integrity."
    exit 1
fi
echo ""

# Step 3: Run Alembic upgrade with timeout
echo "🔄 Running database migrations (timeout: 300s)..."
if ! timeout 300 docker exec wpp_disp_backend python -m alembic upgrade head; then
    echo "❌ Migrations failed or timed out!"
    exit 1
fi

echo "✅ Migrations completed successfully!"

# Step 4: Show current migration version
echo "📊 Current database version:"
docker exec wpp_disp_backend python -m alembic current
