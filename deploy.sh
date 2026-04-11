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

# Load and validate required environment variables
set -a
source "$ENV_FILE"
set +a

REQUIRED_VARS=("DATABASE_URL" "POSTGRES_PASSWORD" "GHL_TOKEN_ENCRYPTION_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo "Please configure $ENV_FILE before deploying."
    exit 1
fi

# Validate GHL config: if GHL_CLIENT_ID is set, all GHL creds must be present
if [ -n "${GHL_CLIENT_ID}" ]; then
    MISSING_VARS=()
    GHL_REQUIRED=("GHL_CLIENT_SECRET" "GHL_REDIRECT_URI" "GHL_WEBHOOK_SECRET")
    for var in "${GHL_REQUIRED[@]}"; do
        if [ -z "${!var}" ]; then
            MISSING_VARS+=("$var")
        fi
    done
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo -e "${RED}❌ GHL_CLIENT_ID is set but missing GHL creds:${NC}"
        for var in "${MISSING_VARS[@]}"; do
            echo "   - $var"
        done
        exit 1
    fi
fi

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

# Guard: ensure we are on the correct branch before pulling
echo "🔍 Checking git branch..."
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
EXPECTED_BRANCH="main"
if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]; then
    echo -e "${RED}❌ Current branch is '${CURRENT_BRANCH}', expected '${EXPECTED_BRANCH}'.${NC}"
    echo "Switch to '${EXPECTED_BRANCH}' before deploying: git checkout ${EXPECTED_BRANCH}"
    exit 1
fi
echo -e "${GREEN}✅ Branch check passed (${CURRENT_BRANCH:-detached HEAD})${NC}"
echo ""

# Guard: ensure at least 1GB of free disk space
echo "🔍 Checking disk space..."
FREE_KB=$(df -k . | awk 'NR==2 {print $4}')
MIN_FREE_KB=$((1 * 1024 * 1024))  # 1 GB in KB
if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
    FREE_HUMAN=$(df -h . | awk 'NR==2 {print $4}')
    echo -e "${RED}❌ Insufficient disk space: ${FREE_HUMAN} free (minimum 1GB required).${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Disk space check passed${NC}"
echo ""

# Guard: fail if placeholder YOUR_DOMAIN still present in deploy.sh or nginx config
echo "🔍 Checking for unconfigured placeholders..."
PLACEHOLDER_FILES=()
if grep -q "YOUR_DOMAIN" deploy.sh 2>/dev/null; then
    PLACEHOLDER_FILES+=("deploy.sh")
fi
if grep -rq "YOUR_DOMAIN" nginx/sites-available/ 2>/dev/null; then
    PLACEHOLDER_FILES+=("nginx/sites-available/")
fi
if [ ${#PLACEHOLDER_FILES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Found unconfigured placeholder 'YOUR_DOMAIN' in:${NC}"
    for f in "${PLACEHOLDER_FILES[@]}"; do
        echo "   - $f"
    done
    echo "Replace 'YOUR_DOMAIN' with your actual domain before deploying."
    exit 1
fi
echo -e "${GREEN}✅ No placeholder strings found${NC}"
echo ""

# Backup database if it exists — abort if backup fails
if docker ps | grep -q wpp_disp_postgres; then
    echo "📦 Creating database backup before deployment..."
    if ! ./scripts/backup-db.sh; then
        echo -e "${RED}❌ Pre-deploy backup failed. Aborting deployment to protect data integrity.${NC}"
        echo "Fix the backup script or resolve disk/permission issues before retrying."
        exit 1
    fi
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
    echo "Running alembic downgrade -1 to revert last migration..."
    docker exec wpp_disp_backend python -m alembic downgrade -1 2>/dev/null || \
        echo -e "${YELLOW}⚠️  alembic downgrade -1 failed or no previous revision — check DB state manually.${NC}"
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
