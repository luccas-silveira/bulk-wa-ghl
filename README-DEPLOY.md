# 🚀 Guia de Deploy - WhatsApp Campaign Management

Documentação completa para deploy da aplicação em VPS.

---

## 📋 Pré-requisitos

### Na sua VPS:
- Ubuntu 20.04+ ou Debian 11+
- Docker 24.0+
- Docker Compose 2.0+
- Nginx (opcional, já incluído no Docker)
- 2GB RAM mínimo (4GB recomendado)
- 20GB disco livre
- Domínio apontando para o IP da VPS

### Localmente:
- Git
- SSH configurado para acessar a VPS

---

## 🔧 Instalação Inicial na VPS

### 1. Instalar Docker e Docker Compose

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Adicionar repositório Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalação
docker --version
docker compose version
```

### 2. Preparar Diretórios

```bash
# Criar diretório da aplicação
sudo mkdir -p /var/www/wpp-disp
sudo chown $USER:$USER /var/www/wpp-disp
cd /var/www/wpp-disp

# Criar diretórios de dados persistentes
sudo mkdir -p /var/lib/wpp_disp/postgres
sudo mkdir -p /var/backups/wpp-disp/postgres
```

---

## 📥 Deploy da Aplicação

### 1. Clonar Repositório

```bash
cd /var/www/wpp-disp
git clone <SEU_REPOSITORIO_GIT> .
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar template de produção
cp .env.production.example .env.production

# Editar com suas credenciais
nano .env.production
```

**Variáveis obrigatórias:**

```bash
# PostgreSQL
POSTGRES_USER=wpp_disp_prod
POSTGRES_PASSWORD=<SENHA_FORTE_ALEATORIA>   # obrigatório — sem default
POSTGRES_DB=wpp_disp_production

# GoHighLevel (obrigatórias quando GHL_CLIENT_ID está setado)
GHL_CLIENT_ID=<SEU_CLIENT_ID>
GHL_CLIENT_SECRET=<SEU_CLIENT_SECRET>
GHL_REDIRECT_URI=https://seu-dominio.com/ghl/oauth/callback
GHL_WEBHOOK_SECRET=<SECRET_ALEATORIO>
GHL_TOKEN_ENCRYPTION_KEY=<GERAR_COM_COMANDO_ABAIXO>

# Aplicação
DEBUG=False
LOG_LEVEL=WARNING
VITE_API_URL=https://seu-dominio.com/api
CORS_ORIGINS=https://seu-dominio.com        # obrigatório quando DEBUG=False
ENABLE_METRICS=true
```

> **Nota sobre GHL:** Se `GHL_CLIENT_ID` não for configurado, os endpoints GHL são desabilitados automaticamente e as demais variáveis GHL não são exigidas. Configure-as apenas se for usar a integração com GoHighLevel.

**Observabilidade:**

- `LOG_LEVEL` controla a verbosidade do backend (`DEBUG`, `INFO`, `WARNING`, `ERROR`); logs já saem em JSON com correlação por request e campanha.
- `ENABLE_METRICS` (padrão `true`) habilita o endpoint `/metrics` com métricas Prometheus de latência, taxa de erro e filas/agendamentos.
- Envie o header `X-Request-ID` (opcional) para propagar o identificador de rastreio em toda a cadeia de logs.

**Gerar chave de criptografia:**

```bash
docker run --rm python:3.13-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Definir permissões:**

```bash
chmod 600 .env.production
```

### 3. Configurar Nginx (com seu domínio)

```bash
# Editar configuração do Nginx
nano nginx/sites-available/wpp-disp.conf

# Substituir YOUR_DOMAIN pelo seu domínio
sed -i 's/YOUR_DOMAIN/seu-dominio.com/g' nginx/sites-available/wpp-disp.conf
```

### 4. Configurar SSL com Let's Encrypt

```bash
# Instalar Certbot
sudo apt install -y certbot

# Gerar certificados
sudo certbot certonly --standalone -d seu-dominio.com -d www.seu-dominio.com

# Copiar certificados para o projeto
sudo cp /etc/letsencrypt/live/seu-dominio.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/seu-dominio.com/privkey.pem nginx/ssl/
sudo chown $USER:$USER nginx/ssl/*.pem

# Configurar renovação automática
sudo crontab -e
# Adicionar linha:
0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/seu-dominio.com/*.pem /var/www/wpp-disp/nginx/ssl/ && docker-compose -f /var/www/wpp-disp/docker-compose.yml -f /var/www/wpp-disp/docker-compose.prod.yml restart nginx
```

### 5. Executar Deploy

```bash
# Primeira vez
./deploy.sh production

# Ou manualmente:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 6. Verificar Saúde dos Serviços

```bash
./scripts/health-check.sh
```

---

## 🔄 Atualizações e Manutenção

### Atualizar Aplicação

```bash
cd /var/www/wpp-disp

# Pull das mudanças
git pull origin main

# Executar deploy novamente
./deploy.sh production
```

### Backup Manual do Banco

```bash
./scripts/backup-db.sh
```

### Restaurar Backup

```bash
# Listar backups disponíveis
ls -lh /var/backups/wpp-disp/postgres/

# Restaurar backup específico
docker exec -i wpp_disp_postgres psql -U wpp_disp_prod -d wpp_disp_production < /var/backups/wpp-disp/postgres/wpp_disp_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Ver Logs

```bash
# Todos os serviços
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Apenas backend
docker-compose logs -f backend

# Apenas frontend
docker-compose logs -f frontend

# Últimas 100 linhas
docker-compose logs --tail=100 backend
```

### Restart de Serviços

```bash
# Todos os serviços
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# Apenas backend
docker-compose restart backend
```

---

## 📊 Monitoramento

### Verificar Status

```bash
# Containers rodando
docker ps

# Uso de recursos
docker stats

# Health check
curl https://seu-dominio.com/api/health
```

### Configurar Backup Automático

```bash
# Editar crontab
crontab -e

# Adicionar backup diário às 3h da manhã
0 3 * * * /var/www/wpp-disp/scripts/backup-db.sh >> /var/log/wpp-disp-backup.log 2>&1
```

### Logs do Sistema

```bash
# Criar rotação de logs
sudo nano /etc/logrotate.d/wpp-disp

# Adicionar:
/var/www/wpp-disp/nginx/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        docker-compose -f /var/www/wpp-disp/docker-compose.yml -f /var/www/wpp-disp/docker-compose.prod.yml restart nginx > /dev/null
    endscript
}
```

---

## 🔒 Segurança

### Firewall

```bash
# Configurar UFW
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Secrets

- **NUNCA** commitar arquivos `.env` ou `.env.production`
- Usar senhas fortes (mínimo 32 caracteres)
- Rotacionar secrets regularmente
- Guardar backup dos secrets em gerenciador de senhas

---

## 🆘 Troubleshooting

### Container não inicia

```bash
# Ver logs
docker-compose logs backend

# Verificar configuração
docker-compose config

# Rebuild sem cache
docker-compose build --no-cache
```

### Banco de dados não conecta

```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Testar conexão
docker exec wpp_disp_postgres pg_isready -U wpp_disp_prod

# Ver logs do PostgreSQL
docker-compose logs postgres
```

### Erro 502 Bad Gateway

```bash
# Verificar se backend está rodando
docker ps | grep backend

# Verificar logs do nginx
docker-compose logs nginx

# Verificar health check
curl http://localhost:8000/health
```

### Migrations falhando

```bash
# Ver status atual
docker exec wpp_disp_backend python -m alembic current

# Ver histórico
docker exec wpp_disp_backend python -m alembic history

# Forçar para última versão (cuidado!)
docker exec wpp_disp_backend python -m alembic upgrade head
```

---

## 📞 Suporte

- **Logs:** `/var/www/wpp-disp/nginx/logs/`
- **Backups:** `/var/backups/wpp-disp/postgres/`
- **Documentação da API:** `https://seu-dominio.com/api/docs`

---

## ✅ Checklist de Deploy

- [ ] Docker e Docker Compose instalados
- [ ] Repositório clonado
- [ ] `.env.production` configurado
- [ ] Domínio apontando para VPS
- [ ] SSL configurado (Let's Encrypt)
- [ ] Nginx configurado com domínio correto
- [ ] Firewall configurado
- [ ] Deploy executado com sucesso
- [ ] Health check passando
- [ ] Backup automático configurado
- [ ] Logs sendo rotacionados
- [ ] Credenciais guardadas em local seguro

---

## 🔄 Workflow de Deploy Contínuo

### Primeira vez:
1. SSH na VPS
2. Clonar repositório
3. Configurar .env.production
4. Configurar SSL
5. Executar `./deploy.sh production`

### Atualizações:
1. SSH na VPS
2. `cd /var/www/wpp-disp`
3. `git pull origin main`
4. `./deploy.sh production`

Pronto! Sua aplicação está no ar. 🎉
