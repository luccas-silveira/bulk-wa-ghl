#!/bin/bash
###############################################################################
# Database Migration Script
# Runs Alembic migrations in the backend container
# Usage: ./scripts/migrate-db.sh
###############################################################################

set -e  # Exit on error

echo "🔄 Running database migrations..."

# Check if backend container is running
if ! docker ps | grep -q wpp_disp_backend; then
    echo "❌ Backend container is not running!"
    echo "Start it with: docker-compose up -d backend"
    exit 1
fi

# Run Alembic upgrade
docker exec wpp_disp_backend \
    python -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully!"

    # Show current migration version
    echo "📊 Current database version:"
    docker exec wpp_disp_backend \
        python -m alembic current
else
    echo "❌ Migrations failed!"
    exit 1
fi
