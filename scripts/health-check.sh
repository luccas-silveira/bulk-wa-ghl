#!/bin/bash
###############################################################################
# Health Check Script
# Checks if all services are running and healthy.
# Exits with code 1 if ANY check fails.
# Usage: ./scripts/health-check.sh
###############################################################################

set -e

FAILED=0

echo "🏥 Checking service health..."
echo ""

# Check Docker containers
echo "📦 Docker Containers:"
docker ps --filter "name=wpp_disp" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check backend health
echo "🔍 Backend Health:"
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    curl -s http://localhost:8000/health | python3 -m json.tool
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    FAILED=1
fi
echo ""

# Check frontend
echo "🌐 Frontend Health:"
if curl -sf http://localhost:3001/ > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
    FAILED=1
fi
echo ""

# Check database
echo "🗄️  Database:"
if docker exec wpp_disp_postgres pg_isready -U "${POSTGRES_USER:-wpp_disp}" > /dev/null 2>&1; then
    echo "✅ PostgreSQL is accepting connections"
else
    echo "❌ PostgreSQL is not responding"
    FAILED=1
fi
echo ""

echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    $(docker ps --filter "name=wpp_disp" -q) 2>/dev/null || true

echo ""
if [ "$FAILED" -eq 1 ]; then
    echo "❌ One or more health checks failed."
    exit 1
fi

echo "✅ All health checks passed."
