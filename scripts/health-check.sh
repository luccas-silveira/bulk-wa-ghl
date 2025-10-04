#!/bin/bash
###############################################################################
# Health Check Script
# Checks if all services are running and healthy
# Usage: ./scripts/health-check.sh
###############################################################################

set -e

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
fi
echo ""

# Check frontend
echo "🌐 Frontend Health:"
if curl -sf http://localhost:3001/health > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "⚠️  Frontend health check not available (expected)"
fi
echo ""

# Check database
echo "🗄️  Database:"
if docker exec wpp_disp_postgres pg_isready -U wpp_disp > /dev/null 2>&1; then
    echo "✅ PostgreSQL is accepting connections"
else
    echo "❌ PostgreSQL is not responding"
fi
echo ""

echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    $(docker ps --filter "name=wpp_disp" -q)
