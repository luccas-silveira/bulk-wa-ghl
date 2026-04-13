# Production Deploy Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy branch `004-campaign-management` to `appzoi.com` (server `147.79.87.179`), substituindo a versão antiga sem interromper os outros 17+ serviços rodando no servidor.

**Architecture:** Backend FastAPI via Docker Compose (porta externa 8001), frontend React/nginx (porta externa 3001), Postgres (porta 5433) — todos atrás do nginx do host em `https://appzoi.com/disparador/`. Os containers postgres não são reconstruídos; apenas backend e frontend são substituídos.

**Tech Stack:** Docker Compose, Alembic, nginx (host), Python 3.12/FastAPI, React/Vite, PostgreSQL 16, aiofiles

---

## Contexto crítico antes de começar

### O que mudou entre produção atual e novo branch

| Item | Produção atual (`a2d7be2`) | Novo branch (`004-campaign-management`) | Ação |
|---|---|---|---|
| `media_upload.py` | ✅ existe, funciona | ❌ removido | Portar no Task 1 |
| `aiofiles` em requirements.txt | ✅ instalado na imagem | ❌ não está | Adicionar no Task 1 |
| `ai_enabled` coluna em campaigns | ✅ na DB | ❌ não está no modelo | Ignorar — SQLAlchemy ignora colunas extras |
| Tabela `campaign_audience` | ✅ na DB | ❌ não está no modelo | Ignorar — tabela extra não causa problema |
| Alembic version na DB | `6d6a176619fc` (cadeia antiga) | Head: `3b4d197b5c0e` | Stamp no Task 4 |
| `.env.production` | ✅ completo com todos os secrets | ✅ mesmo arquivo usado | Nenhuma mudança |
| Nginx config | ✅ `/disparador/` → 3001, `/disparador/api/` → 8001 | ✅ mesma estrutura | Nenhuma mudança |
| Media files `backend/uploads/media/` | ✅ ~30 arquivos reais | Arquivos untracked → preservados pelo git | Nenhuma ação |

### Por que Alembic precisa de stamp (não migrate)

A DB de produção está na versão `6d6a176619fc` (de uma cadeia de migrações diferente). O novo branch tem uma cadeia diferente que termina em `3b4d197b5c0e`. Rodar `alembic upgrade head` quebraria tudo. O `alembic stamp` apenas atualiza o registro de versão sem tocar no schema — seguro porque:
- A DB já tem todas as tabelas que os novos modelos precisam
- Colunas/tabelas extras (`ai_enabled`, `campaign_audience`) são ignoradas pelo SQLAlchemy
- Não há novas colunas no novo branch que não existam na DB

### Como o bind mount afeta o deploy

O `docker-compose.yml` tem `./backend:/app`. Isso significa que o container sempre usa o código do host. Depois do `git checkout`, o container IMEDIATAMENTE vê o novo código (sem rebuild). O rebuild só é necessário para atualizar pacotes Python (quando `requirements.txt` muda).

---

## File Structure

**Arquivos modificados localmente (antes do deploy):**
- Criar: `backend/src/api/media_upload.py`
- Modificar: `backend/requirements.txt` (adicionar `aiofiles`)
- Modificar: `backend/src/main.py` (importar e registrar router de media)

**Arquivos no servidor (durante deploy):**
- Ler: `/var/www/wpp-disp/bulk-wa-ghl/` (diretório do projeto)
- Não tocar: `.env.production`, `backend/uploads/media/*`, `docker-compose.yml`
- Não tocar: nenhum outro container fora de `wpp_disp_backend` e `wpp_disp_frontend`

---

## Task 1: Portar `media_upload.py` para o novo branch (máquina local)

**Contexto:** O endpoint de upload de mídia (`POST /media/upload`) existe em produção mas foi removido do novo branch. Usuários dependem dele para anexar imagens/vídeos em campanhas. Este task roda na máquina local antes do deploy.

**Files:**
- Criar: `backend/src/api/media_upload.py`
- Modificar: `backend/requirements.txt`
- Modificar: `backend/src/main.py`

- [ ] **Step 1: Criar `backend/src/api/media_upload.py`**

```python
"""
Media Upload API
Handles file uploads for campaign messages
"""
import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import aiofiles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media Upload"])

UPLOAD_DIR = Path("/app/uploads/media")
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB (WhatsApp limit)
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "").rstrip("/")
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.mp4', '.avi', '.mov', '.mkv',
    '.mp3', '.ogg', '.wav', '.m4a',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
}


def _get_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _allowed(filename: str) -> bool:
    return _get_ext(filename) in ALLOWED_EXTENSIONS


def _unique_name(original: str) -> str:
    return f"{uuid.uuid4().hex}{_get_ext(original)}"


@router.post("/upload", status_code=201)
async def upload_media(file: UploadFile = File(...)):
    """Upload media file (image/video/audio/document) for campaign messages. Max 25 MB."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if not _allowed(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    contents = await file.read()
    size = len(contents)

    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size / 1024 / 1024:.1f} MB). Max is 25 MB.",
        )

    unique = _unique_name(file.filename)
    async with aiofiles.open(UPLOAD_DIR / unique, "wb") as f:
        await f.write(contents)

    relative_url = f"/uploads/media/{unique}"
    absolute_url = f"{MEDIA_BASE_URL}{relative_url}" if MEDIA_BASE_URL else relative_url

    logger.info("Media uploaded: %s (%d KB)", unique, size // 1024)

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "url": absolute_url,
            "relative_url": relative_url,
            "filename": unique,
            "original_filename": file.filename,
            "size": size,
            "content_type": file.content_type,
        },
    )


@router.delete("/upload/{filename}")
async def delete_media(filename: str):
    """Delete a previously uploaded media file."""
    file_path = UPLOAD_DIR / filename

    # Prevent path traversal
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_path.unlink()
    logger.info("Media deleted: %s", filename)
    return {"success": True, "message": "File deleted"}
```

- [ ] **Step 2: Adicionar `aiofiles` em `backend/requirements.txt`**

Abra `backend/requirements.txt` e adicione após a última dependência existente:

```
aiofiles==23.2.1
```

- [ ] **Step 3: Registrar o router em `backend/src/main.py`**

Localize o bloco de imports de routers no `main.py` (por volta da linha 40) e adicione:

```python
from src.api.media_upload import router as media_upload_router
```

Localize onde os routers são registrados via `app.include_router(...)` e adicione:

```python
app.include_router(media_upload_router)
```

> **Atenção:** Se `GHL_ENABLED` condiciona quais routers são registrados, o media router deve ficar **fora** do bloco condicional (media upload não depende de GHL).

- [ ] **Step 4: Verificar TypeScript + testes backend não quebraram**

```bash
cd frontend && npx tsc --noEmit
```
Expected: sem erros.

```bash
cd backend && python -m pytest tests/unit -q
```
Expected: todos os testes passam.

- [ ] **Step 5: Commit e push**

```bash
git add backend/src/api/media_upload.py backend/requirements.txt backend/src/main.py
git commit -m "feat: restore media_upload router for production deploy"
git push origin 004-campaign-management
```

---

## Task 2: Pre-flight no servidor — backup e auditoria

**Contexto:** Antes de qualquer mudança no servidor, garantir que o banco está salvo e que há espaço em disco.

**Files:** Nenhum código modificado. Comandos via SSH.

- [ ] **Step 1: Conectar no servidor**

```bash
ssh root@147.79.87.179
```

- [ ] **Step 2: Verificar espaço em disco**

```bash
df -h /
```
Expected: pelo menos 5 GB livres. O disco tem 76 GB usados de 193 GB (61%) — estamos bem.

- [ ] **Step 3: Criar diretório de backups**

```bash
mkdir -p /root/backups
```

- [ ] **Step 4: Fazer backup do banco de produção**

```bash
# Lê credenciais do .env.production
cd /var/www/wpp-disp/bulk-wa-ghl
PG_USER=$(grep ^POSTGRES_USER .env.production | cut -d= -f2)
PG_DB=$(grep ^POSTGRES_DB .env.production | cut -d= -f2)
BACKUP_FILE="/root/backups/wpp_disp_$(date +%Y%m%d_%H%M%S).sql.gz"

docker exec wpp_disp_postgres pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$BACKUP_FILE"
echo "Backup: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
```
Expected: arquivo `.sql.gz` com tamanho maior que 0. Tamanho típico: 50 KB–5 MB.

- [ ] **Step 5: Verificar integridade do backup**

```bash
gunzip -t "$BACKUP_FILE" && echo "Backup OK"
```
Expected: `Backup OK` sem erros.

- [ ] **Step 6: Confirmar containers rodando antes da mudança**

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep wpp_disp
```
Expected:
```
wpp_disp_backend    Up X days (healthy)
wpp_disp_frontend   Up X days (healthy)
wpp_disp_postgres   Up X days (healthy)
```

---

## Task 3: Atualizar código no servidor

**Contexto:** O servidor tem a branch antiga com mudanças locais não commitadas. Fazemos `git stash` para salvar e depois fazemos checkout do novo branch. Os arquivos de mídia (`backend/uploads/media/`) são untracked e NÃO serão tocados pelo git.

- [ ] **Step 1: Entrar no diretório do projeto**

```bash
cd /var/www/wpp-disp/bulk-wa-ghl
```

- [ ] **Step 2: Verificar branch atual e mudanças locais**

```bash
git status --short | head -20
git branch
```
Expected: branch antiga (provavelmente `main` ou sem nome de branch rastreado), arquivos `M` listados.

- [ ] **Step 3: Salvar mudanças locais com stash**

```bash
git stash push -m "producao-local-changes-backup-$(date +%Y%m%d)"
```
Expected: `Saved working directory and index state...`

- [ ] **Step 4: Fetch das novas branches**

```bash
git fetch origin
```
Expected: download dos objetos do `004-campaign-management`.

- [ ] **Step 5: Checkout do novo branch**

```bash
# Se a branch local não existir ainda:
git checkout -b 004-campaign-management origin/004-campaign-management
# Se já existir:
# git checkout 004-campaign-management
```
Expected: `Branch '004-campaign-management' set up to track remote branch '004-campaign-management' from 'origin'.` ou `Switched to branch '004-campaign-management'`.

- [ ] **Step 6: Pull para garantir código mais recente**

```bash
git pull origin 004-campaign-management
```
Expected: `Already up to date.` ou lista de arquivos atualizados incluindo `backend/src/api/media_upload.py`.

- [ ] **Step 7: Verificar que media_upload.py chegou**

```bash
ls backend/src/api/media_upload.py
grep 'aiofiles' backend/requirements.txt
```
Expected: arquivo existe; `aiofiles==23.2.1` na saída do grep.

- [ ] **Step 8: Verificar que media files NÃO foram apagados**

```bash
ls backend/uploads/media/ | wc -l
```
Expected: mesmo número de arquivos de antes (≥ 1, tipicamente ~30).

---

## Task 4: Corrigir versão do Alembic

**Contexto:** A DB de produção está na versão `6d6a176619fc` (cadeia antiga). O novo branch termina em `3b4d197b5c0e`. Precisamos fazer `stamp` para registrar a nova versão **sem rodar nenhuma migration**. O container `wpp_disp_backend` ainda está rodando com o código antigo, mas via bind mount já vê os novos arquivos de alembic — isso é suficiente para o stamp.

- [ ] **Step 1: Verificar versão atual na DB**

```bash
docker exec wpp_disp_postgres psql \
  -U $(grep ^POSTGRES_USER /var/www/wpp-disp/bulk-wa-ghl/.env.production | cut -d= -f2) \
  -d $(grep ^POSTGRES_DB /var/www/wpp-disp/bulk-wa-ghl/.env.production | cut -d= -f2) \
  -c 'SELECT version_num FROM alembic_version;'
```
Expected:
```
 version_num  
--------------
 6d6a176619fc
(1 row)
```

- [ ] **Step 2: Fazer stamp para o novo head**

```bash
docker exec wpp_disp_backend alembic -c /app/alembic.ini stamp 3b4d197b5c0e
```
Expected: saída sem erros como `Running stamp for revision 3b4d197b5c0e` ou sem output (sucesso silencioso).

> **Se o comando falhar com "Can't locate revision":** Verifique se o git pull do Task 3 incluiu o arquivo `backend/alembic/versions/3b4d197b5c0e_merge_phone_and_state_machine.py`. Se não, o novo código ainda não chegou.

- [ ] **Step 3: Confirmar stamp aplicado**

```bash
docker exec wpp_disp_postgres psql \
  -U $(grep ^POSTGRES_USER /var/www/wpp-disp/bulk-wa-ghl/.env.production | cut -d= -f2) \
  -d $(grep ^POSTGRES_DB /var/www/wpp-disp/bulk-wa-ghl/.env.production | cut -d= -f2) \
  -c 'SELECT version_num FROM alembic_version;'
```
Expected:
```
 version_num  
--------------
 3b4d197b5c0e
(1 row)
```

---

## Task 5: Rebuild das imagens Docker e restart

**Contexto:** Reconstruímos apenas `backend` e `frontend`. O container `postgres` NÃO é tocado — ele está healthy há 6 dias com dados reais. O `--build` reconstrói as imagens com o novo código e novas dependências (incluindo `aiofiles`). O postgres usa `image:` (sem `build:`), então o `--build` simplesmente o ignora.

- [ ] **Step 1: Confirmar que estamos no diretório correto**

```bash
cd /var/www/wpp-disp/bulk-wa-ghl
ls docker-compose.yml .env.production
```
Expected: ambos os arquivos existem.

- [ ] **Step 2: Rebuild e restart de backend e frontend**

```bash
docker-compose up -d --build backend frontend 2>&1 | tee /tmp/deploy-$(date +%Y%m%d_%H%M%S).log
```
Expected: output como:
```
Building backend ... done
Building frontend ... done
Recreating wpp_disp_backend ... done
Recreating wpp_disp_frontend ... done
```
O build do backend pode levar 3–5 minutos (pip install). O frontend pode levar 2–3 minutos (npm ci + vite build).

- [ ] **Step 3: Verificar que postgres não foi tocado**

```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep wpp_disp_postgres
```
Expected: `wpp_disp_postgres   Up X days (healthy)` — mesmo uptime de antes.

- [ ] **Step 4: Aguardar health checks passarem**

```bash
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep wpp_disp'
```
Aguardar até `wpp_disp_backend` e `wpp_disp_frontend` mostrarem `(healthy)`. Sair com `Ctrl+C`.
Expected: ambos healthy em até 2 minutos após o start.

---

## Task 6: Smoke test — verificar deploy

**Contexto:** Validar que tudo está funcionando via chamadas HTTP reais. Testar tanto o backend diretamente (porta 8001) quanto através do nginx (domínio público).

- [ ] **Step 1: Health check no backend direto**

```bash
curl -sf http://localhost:8001/health && echo " OK"
```
Expected: `OK` (HTTP 200).

- [ ] **Step 2: Health check via nginx (domínio público)**

```bash
curl -sf https://appzoi.com/disparador/api/health && echo " OK"
```
Expected: `OK` (HTTP 200).

- [ ] **Step 3: Verificar API de campanhas**

```bash
# Direto no backend (porta 8001 local)
curl -s http://localhost:8001/api/v1/campaigns | python3 -m json.tool | head -20
```
Expected: JSON com `{"campaigns": [...], "total": N, ...}` — pode ser lista vazia, desde que não seja erro 500.

- [ ] **Step 4: Verificar docs da API**

```bash
curl -sf https://appzoi.com/disparador/api/docs -o /dev/null -w "%{http_code}"
```
Expected: `200`.

- [ ] **Step 5: Verificar frontend carrega**

```bash
curl -sf https://appzoi.com/disparador/ -o /dev/null -w "%{http_code}"
```
Expected: `200`.

- [ ] **Step 6: Verificar logs do backend por erros**

```bash
docker logs wpp_disp_backend --tail 50 2>&1 | grep -E 'ERROR|CRITICAL|Traceback' || echo "Nenhum erro encontrado"
```
Expected: `Nenhum erro encontrado` ou apenas erros esperados de startup (como GHL_ENABLED=False).

- [ ] **Step 7: Verificar que rota `/embedded` funciona (nova feature)**

```bash
curl -sf "https://appzoi.com/disparador/embedded?embedded=true&ghl_location_id=test&ghl_user_id=test" -o /dev/null -w "%{http_code}"
```
Expected: `200` (nginx serve a SPA; React Router cuida do roteamento client-side).

- [ ] **Step 8: Verificar endpoint de media upload**

```bash
curl -s -X POST https://appzoi.com/disparador/api/media/upload \
  -F "file=@/etc/hostname" \
  | python3 -m json.tool
```
Expected: `{"success": true, "url": "https://appzoi.com/uploads/media/...", ...}` (o arquivo `hostname` tem extensão sem `.` então pode falhar com "File type not allowed" — isso é correto! O importante é receber HTTP 400 com esse detail, não 404/500.)

- [ ] **Step 9: Verificar outros serviços não foram afetados**

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -v wpp_disp
```
Expected: todos os outros containers ainda estão `Up X days` (uptime inalterado).

---

## Rollback (se algo der errado)

Se o deploy falhar e precisar reverter:

```bash
cd /var/www/wpp-disp/bulk-wa-ghl

# Voltar para a branch antiga
git checkout -

# Restaurar as mudanças locais da produção
git stash pop

# Corrigir alembic version de volta
docker exec wpp_disp_backend alembic -c /app/alembic.ini stamp 6d6a176619fc

# Rebuildar com o código antigo
docker-compose up -d --build backend frontend
```

Se o banco estiver corrompido, restaurar o backup:
```bash
BACKUP_FILE=$(ls -t /root/backups/wpp_disp_*.sql.gz | head -1)
PG_USER=$(grep ^POSTGRES_USER /var/www/wpp-disp/bulk-wa-ghl/.env.production | cut -d= -f2)
PG_DB=$(grep ^POSTGRES_DB /var/www/wpp-disp/bulk-wa-ghl/.env.production | cut -d= -f2)

docker exec -i wpp_disp_postgres psql -U "$PG_USER" -d "$PG_DB" < <(gunzip -c "$BACKUP_FILE")
```
