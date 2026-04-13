# Runbook de Operações — wpp-disp

Guia operacional para deploy, rollback, backup, restore e resposta a incidentes do sistema de campanhas WhatsApp via GHL.

---

## Índice

1. [Visão geral da infraestrutura](#1-visão-geral-da-infraestrutura)
2. [Primeiro deploy (ambiente novo)](#2-primeiro-deploy-ambiente-novo)
3. [Deploy de atualização](#3-deploy-de-atualização)
4. [Rollback](#4-rollback)
5. [Backup e restore](#5-backup-e-restore)
6. [Migrações de banco de dados](#6-migrações-de-banco-de-dados)
7. [Health checks e monitoramento](#7-health-checks-e-monitoramento)
8. [Operações de campanha](#8-operações-de-campanha)
9. [Resposta a incidentes](#9-resposta-a-incidentes)
10. [Rotinas periódicas](#10-rotinas-periódicas)
11. [Referência rápida de comandos](#11-referência-rápida-de-comandos)

---

## 1. Visão geral da infraestrutura

### Serviços (Docker Compose)

| Container | Imagem | Porta interna | Exposta para |
|-----------|--------|--------------|--------------|
| `wpp_disp_postgres` | postgres:16 | 5432 | 127.0.0.1:5432 |
| `wpp_disp_backend` | ./backend | 8000 | 127.0.0.1:8000 |
| `wpp_disp_frontend` | ./frontend | 80 | 127.0.0.1:3001 |
| `wpp_disp_nginx` | nginx:alpine | 80, 443 | 0.0.0.0:80, 443 |

Nginx atua como reverse proxy: todo tráfego externo entra por ele. Backend e frontend não são expostos diretamente.

### Dados persistidos

- **Banco de dados:** `/var/lib/wpp_disp/postgres` (volume Docker, produção)
- **Backups:** `/var/backups/wpp-disp/postgres/` (no host, fora do Docker)
- **Logs Nginx:** `./nginx/logs/`

### Variáveis de ambiente obrigatórias em produção

```
DATABASE_URL          — string de conexão PostgreSQL (postgresql+asyncpg://...)
POSTGRES_PASSWORD     — senha do PostgreSQL
GHL_TOKEN_ENCRYPTION_KEY — chave Fernet para criptografar tokens OAuth
CORS_ORIGINS          — origens permitidas (ex: https://seu-dominio.com)
BACKUP_ENCRYPTION_KEY — chave para criptografar backups
```

Se `GHL_CLIENT_ID` estiver definido, estas também são obrigatórias:
```
GHL_CLIENT_SECRET, GHL_REDIRECT_URI, GHL_WEBHOOK_SECRET
```

---

## 2. Primeiro deploy (ambiente novo)

### 2.1 Pré-requisitos

- Docker e Docker Compose instalados
- Git instalado
- Certificado SSL em `./nginx/ssl/` (ou Let's Encrypt configurado)
- Domínio configurado no DNS apontando para o servidor

### 2.2 Passos

```bash
# 1. Clonar o repositório
git clone <repo-url> /opt/wpp-disp
cd /opt/wpp-disp
git checkout main

# 2. Criar arquivo de configuração
cp .env.example .env.production
# Editar .env.production com os valores reais (ver seção de variáveis)

# 3. Gerar GHL_TOKEN_ENCRYPTION_KEY (se não tiver)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4. Configurar domínio no Nginx
# Substituir YOUR_DOMAIN em nginx/sites-available/ pelo domínio real
sed -i 's/YOUR_DOMAIN/seu-dominio.com/g' nginx/sites-available/wpp-disp.conf
# Verificar se não há mais ocorrências
grep -r "YOUR_DOMAIN" nginx/ deploy.sh

# 5. Criar diretório de backups
mkdir -p /var/backups/wpp-disp/postgres

# 6. Banco de dados novo — aplicar migrations diretamente
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres
sleep 5
docker exec wpp_disp_backend python -m alembic upgrade head
# Isso aplica as duas revisions em sequência: eb03c3cc8781 → a8f3c2e7d1b9

# 7. Deploy completo
./deploy.sh production
```

### 2.3 Banco de dados já existente (migração de servidor)

Se o banco já tem dados (staging → produção ou troca de servidor):

```bash
# IMPORTANTE: stamp o baseline primeiro para evitar re-executar o schema inicial
docker exec wpp_disp_backend python -m alembic stamp eb03c3cc8781

# Depois aplicar apenas as migrations incrementais
docker exec wpp_disp_backend python -m alembic upgrade head
```

---

## 3. Deploy de atualização

O script `deploy.sh production` executa a sequência completa com segurança:

```bash
cd /opt/wpp-disp
./deploy.sh production
```

**O que o script faz automaticamente:**
1. Valida variáveis de ambiente e branch (`main`)
2. Verifica espaço em disco (mínimo 1 GB livre)
3. Detecta `YOUR_DOMAIN` não substituído e aborta
4. Faz backup do banco antes de qualquer mudança
5. `git pull origin main`
6. `docker-compose build` + `up -d`
7. Roda `./scripts/migrate-db.sh` (com rollback automático em falha)
8. Executa `./scripts/health-check.sh`

**Se o deploy falhar na etapa de migration**, o script já tenta `alembic downgrade -1` e para os serviços. Verificar logs antes de reiniciar:

```bash
docker-compose logs backend | tail -50
docker exec wpp_disp_backend python -m alembic current
```

---

## 4. Rollback

### 4.1 Rollback de código (sem migration)

```bash
# Ver commits recentes
git log --oneline -10

# Reverter para commit específico
git checkout <commit-hash>
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
./scripts/health-check.sh
```

### 4.2 Rollback de migration (uma revision)

```bash
# Ver estado atual
docker exec wpp_disp_backend python -m alembic current

# Reverter uma revision
docker exec wpp_disp_backend python -m alembic downgrade -1

# Confirmar novo estado
docker exec wpp_disp_backend python -m alembic current
```

### 4.3 Rollback completo via restore de backup

Usar quando o rollback de código + migration não é suficiente (dados corrompidos, migration irreversível). Ver [seção 5.2](#52-restore-de-backup).

---

## 5. Backup e restore

### 5.1 Backup manual

```bash
# Requer BACKUP_ENCRYPTION_KEY no ambiente ou no .env
export BACKUP_ENCRYPTION_KEY="sua-chave-aqui"

./scripts/backup-db.sh
```

O script:
- Faz `pg_dump` comprimido com gzip
- Verifica integridade com `gunzip -t`
- Criptografa com AES-256-CBC (`openssl enc -aes-256-cbc -pbkdf2`)
- Salva em `/var/backups/wpp-disp/postgres/wpp_disp_backup_YYYYMMDD_HHMMSS.sql.gz.enc`
- Mantém apenas os últimos 10 backups

### 5.2 Restore de backup

```bash
# 1. Parar backend para evitar escritas durante restore
docker-compose stop backend

# 2. Listar backups disponíveis
ls -lh /var/backups/wpp-disp/postgres/

# 3. Descriptografar o backup escolhido
BACKUP_FILE="/var/backups/wpp-disp/postgres/wpp_disp_backup_20261201_120000.sql.gz.enc"
openssl enc -d -aes-256-cbc -pbkdf2 \
    -pass "pass:${BACKUP_ENCRYPTION_KEY}" \
    -in "${BACKUP_FILE}" \
    -out /tmp/restore.sql.gz

# 4. Descomprimir
gunzip /tmp/restore.sql.gz

# 5. Dropar banco atual e recriar (DESTRUTIVO — confirme antes)
docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" wpp_disp_postgres \
    psql -U wpp_disp -d postgres \
    -c "DROP DATABASE IF EXISTS wpp_disp_db; CREATE DATABASE wpp_disp_db OWNER wpp_disp;"

# 6. Restaurar dump
docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" wpp_disp_postgres \
    psql -U wpp_disp -d wpp_disp_db < /tmp/restore.sql

# 7. Remover arquivo temporário
rm /tmp/restore.sql

# 8. Reiniciar backend
docker-compose start backend
sleep 5
./scripts/health-check.sh
```

### 5.3 Verificar integridade de backup sem restore

```bash
BACKUP_FILE="/var/backups/wpp-disp/postgres/wpp_disp_backup_XXX.sql.gz.enc"
openssl enc -d -aes-256-cbc -pbkdf2 \
    -pass "pass:${BACKUP_ENCRYPTION_KEY}" \
    -in "${BACKUP_FILE}" | gunzip -t && echo "OK" || echo "CORROMPIDO"
```

---

## 6. Migrações de banco de dados

### 6.1 Aplicar migrations pendentes

```bash
./scripts/migrate-db.sh
```

O script faz backup automático antes de migrar.

### 6.2 Verificar estado atual

```bash
# Revision aplicada
docker exec wpp_disp_backend python -m alembic current

# Histórico completo
docker exec wpp_disp_backend python -m alembic history --verbose
```

### 6.3 Revisions conhecidas

| Revision | Descrição |
|----------|-----------|
| `eb03c3cc8781` | Initial schema — 7 tabelas base |
| `a8f3c2e7d1b9` | Timezone fixes (TIMESTAMP → TIMESTAMPTZ) |

### 6.4 Gerar nova migration após alterar models

```bash
# Dentro do container ou com o backend rodando localmente
cd backend
alembic revision --autogenerate -m "descrição da mudança"

# Revisar o arquivo gerado antes de aplicar
# Aplicar
alembic upgrade head
```

**Atenção R01:** Em banco já populado (staging/produção), sempre usar `alembic stamp eb03c3cc8781` antes do primeiro `alembic upgrade head` para não tentar recriar tabelas existentes.

---

## 7. Health checks e monitoramento

### 7.1 Health check completo

```bash
./scripts/health-check.sh
```

Verifica: containers rodando, `/health` do backend, frontend respondendo, PostgreSQL aceitando conexões.

### 7.2 Health check rápido manual

```bash
# Backend
curl -s http://localhost:8000/health | python3 -m json.tool

# Resposta esperada (exemplo):
# {
#   "status": "healthy",
#   "database": "connected",
#   "ghl_enabled": true/false
# }
```

### 7.3 Métricas Prometheus

```bash
# Protegido por token em produção (DEBUG=False)
curl -H "Authorization: Bearer ${METRICS_TOKEN}" http://localhost:8000/metrics
```

Métricas de negócio disponíveis: `messages_sent_total`, `campaign_delivery_rate`, `active_campaigns_total`.

### 7.4 Logs

```bash
# Seguir logs do backend em tempo real
docker-compose logs -f backend

# Últimas 100 linhas de todos os serviços
docker-compose logs --tail=100

# Logs do nginx
tail -f ./nginx/logs/access.log
tail -f ./nginx/logs/error.log

# Filtrar por X-Request-ID para rastrear uma requisição específica
docker-compose logs backend | grep "req_id_aqui"
```

Os logs do backend são JSON estruturado com `X-Request-ID` propagado. Campos chave: `level`, `message`, `request_id`, `campaign_id`.

### 7.5 Uso de recursos

```bash
docker stats --no-stream \
    wpp_disp_postgres wpp_disp_backend wpp_disp_frontend wpp_disp_nginx
```

---

## 8. Operações de campanha

### 8.1 Velocidades de envio

| Velocidade | Delay entre contatos |
|------------|---------------------|
| `slow` | 420 segundos (~7 min) |
| `medium` | 240 segundos (~4 min) |
| `fast` | 60 segundos (1 min) |

Uma campanha com 100 contatos no modo `medium` leva ~6,6 horas. Planejar execuções com antecedência.

### 8.2 Estados válidos de campanha

```
draft → scheduled | executing | failed
executing → paused | completed | failed
paused → executing
scheduled → cancelled | failed | executing
```

Estados terminais (`completed`, `failed`, `cancelled`) não têm transições de saída.

### 8.3 Checar campanhas presas em `executing`

Se o backend reiniciar durante uma campanha em execução, ela pode ficar com `status = executing` mas sem processo ativo. Checar via API:

```bash
curl -s "http://localhost:8000/api/v1/campaigns?status=executing" | python3 -m json.tool
```

Para retomar: usar o endpoint `POST /api/v1/campaigns/{id}/resume` ou corrigir o status diretamente no banco (último recurso):

```bash
# APENAS se necessário — preferir a API
docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" wpp_disp_postgres \
    psql -U wpp_disp -d wpp_disp_db \
    -c "UPDATE campaigns SET status='paused' WHERE id=<id> AND status='executing';"
```

### 8.4 Limpeza de webhooks processados

O APScheduler roda diariamente (no lifespan do FastAPI) para deletar `processed_webhooks` com mais de 30 dias. Verificar se o job está ativo:

```bash
docker-compose logs backend | grep "_cleanup_old_webhooks"
```

---

## 9. Resposta a incidentes

### 9.1 Backend não responde (HTTP 502/503)

```bash
# 1. Verificar container
docker ps | grep wpp_disp_backend

# 2. Ver últimos logs de erro
docker-compose logs --tail=50 backend

# 3. Tentar reiniciar
docker-compose restart backend
sleep 10
curl -s http://localhost:8000/health

# 4. Se persistir — verificar banco de dados
docker ps | grep wpp_disp_postgres
curl -s http://localhost:8000/health  # "database": "connected" ou erro
```

### 9.2 Banco de dados não conecta

```bash
# Verificar container postgres
docker ps | grep wpp_disp_postgres

# Checar se aceita conexões
docker exec wpp_disp_postgres pg_isready -U wpp_disp

# Ver logs do postgres
docker-compose logs postgres | tail -30

# Reiniciar apenas o postgres (pode causar campanhas falhando — aceitável)
docker-compose restart postgres
sleep 5
docker exec wpp_disp_postgres pg_isready -U wpp_disp

# Reiniciar backend para restabelecer pool de conexões
docker-compose restart backend
```

### 9.3 Erro de startup: variável obrigatória ausente

O backend recusa iniciar sem `DATABASE_URL`. Verificar o log:

```bash
docker-compose logs backend | grep -i "missing\|required\|startup\|error"
```

Erros comuns:
- `DATABASE_URL not set` — adicionar ao `.env.production`
- `CORS_ORIGINS must be set in production` — necessário quando `DEBUG=False`
- `GHL_CLIENT_SECRET required when GHL_CLIENT_ID is set` — completar credenciais GHL

### 9.4 Campanha não inicia após criação

1. Checar se `status = scheduled` e se o APScheduler registrou o job:
   ```bash
   docker-compose logs backend | grep "scheduler\|scheduled\|campaign_id"
   ```
2. Se `status = failed`, checar `failure_reason` via API:
   ```bash
   curl -s http://localhost:8000/api/v1/campaigns/<id> | python3 -m json.tool
   ```
3. Verificar se GHL está ativo e token válido:
   ```bash
   curl -s http://localhost:8000/docs-status | python3 -m json.tool
   # "ghl_enabled": true/false
   ```

### 9.5 Alto uso de memória / CPU

```bash
# Ver uso por container
docker stats --no-stream wpp_disp_backend wpp_disp_postgres

# Limites configurados (docker-compose.prod.yml):
# backend: 2 CPUs, 2 GB RAM
# postgres: 2 CPUs, 1 GB RAM
# nginx: 1 CPU, 256 MB RAM
# frontend: 0.5 CPU, 256 MB RAM
```

Se o backend estiver no limite, verificar campanhas em execução simultânea — `asyncio.create_task()` cria tasks em paralelo por campanha.

### 9.6 Vazamento de dados PII nos logs

O `ContextFilter` mascara telefones (`+\d{7,15}` → `+***`) automaticamente. Se telefones aparecerem em claro nos logs, verificar se o filtro está registrado:

```bash
docker-compose logs backend | grep -o '+[0-9]\{7,15\}' | head -5
# Resultado esperado: nenhum (tudo mascarado como +***)
```

Se aparecerem números reais: reiniciar o backend e abrir issue — o filtro pode não ter sido aplicado em um path de log específico.

---

## 10. Rotinas periódicas

### Diária (automatizada)
- Backup do banco via `deploy.sh` em cada deploy
- Limpeza de `processed_webhooks` > 30 dias (APScheduler, automático)

### Semanal (manual)
```bash
# Verificar backups disponíveis
ls -lh /var/backups/wpp-disp/postgres/

# Verificar espaço em disco
df -h /var/lib/wpp_disp /var/backups

# Health check geral
./scripts/health-check.sh
```

### Mensal (manual)
```bash
# Testar restore em ambiente de staging
# (ver seção 5.2 — nunca testar restore em produção com dados reais)

# Verificar certificado SSL
openssl s_client -connect seu-dominio.com:443 -servername seu-dominio.com \
    2>/dev/null | openssl x509 -noout -dates

# Rodar Lighthouse para checar acessibilidade > 90
npx lighthouse https://seu-dominio.com --only-categories=accessibility --output=json
```

---

## 11. Referência rápida de comandos

### Deploy e controle de serviços

```bash
# Deploy completo
./deploy.sh production

# Parar todos os serviços
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Reiniciar serviço específico
docker-compose restart backend
docker-compose restart postgres

# Ver status de todos os containers
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f [backend|postgres|frontend|nginx]
```

### Banco de dados

```bash
# Backup manual
./scripts/backup-db.sh

# Aplicar migrations
./scripts/migrate-db.sh

# Versão atual do schema
docker exec wpp_disp_backend python -m alembic current

# Shell do PostgreSQL
docker exec -it -e PGPASSWORD="${POSTGRES_PASSWORD}" wpp_disp_postgres \
    psql -U wpp_disp -d wpp_disp_db
```

### Diagnóstico

```bash
# Health check completo
./scripts/health-check.sh

# Backend health rápido
curl -s http://localhost:8000/health

# Endpoints registrados (reflete GHL_ENABLED)
curl -s http://localhost:8000/docs-status

# Recursos por container
docker stats --no-stream

# Espaço em disco
df -h /var/lib/wpp_disp /var/backups
```
