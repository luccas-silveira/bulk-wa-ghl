#!/bin/bash
###############################################################################
# Deployment Script for WhatsApp Campaign Management
# Handles full deployment workflow with safety checks
# Usage: ./deploy.sh [production|staging]
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENV=${1:-production}
COMPOSE_FILES="-f docker-compose.yml"

if [ "$ENV" == "production" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

echo -e "${GREEN}🚀 WhatsApp Campaign Deployment${NC}"
echo -e "${YELLOW}Environment: $ENV${NC}"
echo ""

# Pre-deployment checks
echo "🔍 Running pre-deployment checks..."

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ $ENV_FILE not found!${NC}"
    echo "Copy .env.example to $ENV_FILE and configure it."
    exit 1
fi

# Validate required environment variables
echo "🔑 Validating required environment variables..."
source "$ENV_FILE"

MISSING_VARS=()
for VAR in POSTGRES_PASSWORD GHL_CLIENT_ID GHL_CLIENT_SECRET GHL_TOKEN_ENCRYPTION_KEY GHL_WEBHOOK_SECRET GHL_REDIRECT_URI; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "   - $VAR"
    done
    echo "Set these in $ENV_FILE before deploying."
    exit 1
fi
echo -e "${GREEN}✅ All required environment variables are set${NC}"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pre-deployment checks passed${NC}"
echo ""

# Backup database if it exists
if docker ps | grep -q wpp_disp_postgres; then
    echo "📦 Creating database backup before deployment..."
    ./scripts/backup-db.sh || echo "⚠️  Backup failed, continuing anyway..."
    echo ""
fi

# Pull latest changes (if using Git)
if [ -d .git ]; then
    echo "📥 Pulling latest changes from Git..."
    git pull origin $(git branch --show-current)
    echo ""
fi

# Build and deploy
echo "🏗️  Building Docker images..."
docker-compose $COMPOSE_FILES build

echo ""
echo "🚀 Starting services..."
docker-compose $COMPOSE_FILES up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Run migrations with rollback on failure
echo "🔄 Running database migrations..."
if ! ./scripts/migrate-db.sh; then
    echo ""
    echo -e "${RED}❌ Migration failed! Rolling back...${NC}"
    docker-compose $COMPOSE_FILES down
    echo "Services stopped. Please fix the migration and redeploy."
    exit 1
fi

echo ""
echo "🏥 Running health checks..."
./scripts/health-check.sh

echo ""
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo ""
echo "📊 Service URLs:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3001"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📝 View logs with: docker-compose logs -f"
echo "🛑 Stop services with: docker-compose down"
