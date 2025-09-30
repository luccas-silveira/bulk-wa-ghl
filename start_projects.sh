#!/bin/bash

echo "🚀 Iniciando WhatsApp Campaign Management - Melhorias da Interface"
echo "================================================================"

# Backend
echo ""
echo "📡 Iniciando Backend (FastAPI) na porta 8000..."
cd backend

# Verificar se o virtual environment existe
if [ ! -d "venv" ]; then
    echo "Criando virtual environment..."
    python3 -m venv venv
fi

# Ativar virtual environment e instalar dependências
echo "Ativando virtual environment e instalando dependências..."
source venv/bin/activate
pip install fastapi uvicorn httpx httpcore anyio pydantic sqlalchemy psycopg2-binary alembic python-multipart

# Iniciar backend
echo "Iniciando servidor backend..."
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Frontend
echo ""
echo "🎨 Iniciando Frontend (React + Vite) na porta 3001..."
cd ../frontend

# Verificar se node_modules existe
if [ ! -d "node_modules" ]; then
    echo "Instalando dependências do frontend..."
    npm install
fi

# Iniciar frontend
echo "Iniciando servidor frontend..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Projetos iniciados com sucesso!"
echo ""
echo "🔗 URLs para acesso:"
echo "   Backend API:     http://localhost:8000"
echo "   API Docs:        http://localhost:8000/docs"
echo "   Frontend:        http://localhost:3001"
echo ""
echo "📋 Funcionalidades implementadas:"
echo "   ✅ Dashboard sem necessidade de User ID"
echo "   ✅ API de sessões WAHA (/waha/sessions)"
echo "   ✅ Dropdown de sessões WAHA no Campaign Wizard"
echo "   ✅ Remoção do campo GHL Team ID"
echo "   ✅ Frontend na porta 3001 (resolve conflito com WAHA)"
echo ""
echo "⏹️  Para parar os serviços, use Ctrl+C"

# Aguardar
wait