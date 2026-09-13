# Planna

Painel financeiro doméstico com integração Open Finance, notas fiscais eletrônicas e insights por IA.

## Funcionalidades

- **Autenticação por magic link** - login sem senha via e-mail, com suporte a households compartilhados (casais, famílias)
- **Open Finance (Pluggy)** - conexão com bancos e cartões de crédito brasileiros para sincronização automática de contas, saldos e transações
- **Extrato unificado** - visão consolidada de todas as contas, com categorização automática e filtros por período, categoria e membro
- **KPIs financeiros** - receita, despesa, saldo e patrimônio líquido do período, com variação percentual em relação ao período anterior
- **Tendências** - gráfico mensal de receita vs. despesa dos últimos 12 meses
- **Despesas por categoria** - distribuição dos gastos por categoria no período selecionado
- **Patrimônio** - ativos (contas, investimentos, previdência, imóveis), passivos (empréstimos, financiamentos, cartões) e patrimônio líquido com histórico mensal
- **Notas fiscais** - ingestão de NFC-e via link ou QR code, com parsing da SEFAZ, conciliação automática com transações bancárias e detalhamento por item
- **Insights financeiros por IA** - análise dos últimos 12 meses com detecção de outliers, gastos recorrentes, risco de fluxo de caixa, composição de renda e eficiência. Textos reescritos e priorizados pela OpenAI (opcional, com consentimento)
- **PWA** - instalável em dispositivos móveis com suporte offline para dados já carregados
- **Observabilidade** - logs estruturados em JSON, health/readiness checks, métricas de sync e custo de IA
- **Backup automático** - dumps diários do PostgreSQL com retenção configurável

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, Pydantic |
| Banco | PostgreSQL 17 |
| Frontend | Next.js 16, React 19, Tailwind CSS 4, shadcn/ui, Lucide |
| Integrações | Pluggy (Open Finance), SEFAZ (NFC-e), OpenAI (insights) |
| Infra | Docker Compose, uv (gerenciador de pacotes Python) |

## Pré-requisitos

- Docker e Docker Compose
- Python 3.11+ e [uv](https://docs.astral.sh/uv/)
- Node.js 20+ e npm

## Instalação

### 1. PostgreSQL

```bash
docker compose up -d postgres
```

O banco fica acessível em `localhost:5433` (porta customizável via `POSTGRES_PORT`).

### 2. Backend

```bash
cd backend
cp .env.example .env
# Edite .env e preencha pelo menos o COOKIE_SECRET (veja seção de variáveis abaixo)
uv sync
uv run alembic upgrade head
```

Cadastre o household inicial:

```bash
uv run python -m app.bootstrap "Minha Casa" "Nome:email@exemplo.com"
```

Cada argumento após o nome do household segue o formato `Nome:email`. O primeiro membro recebe role `owner`, os demais `member`. Exemplo com dois membros:

```bash
uv run python -m app.bootstrap "Casa" "João:joao@email.com" "Maria:maria@email.com"
```

Inicie o servidor:

```bash
uv run fastapi dev --port 8010
```

Em desenvolvimento sem SMTP configurado, o magic link aparece no terminal do backend.

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local
# API_URL=http://127.0.0.1:8010 (padrão)
npm install
npm run dev
```

Abra `http://localhost:3000`. A API fica disponível em `http://localhost:8010/docs`.

### Alternativa: tudo via Docker

```bash
cp backend/.env.example backend/.env
docker compose up -d --build backend
docker compose exec backend uv run --frozen --no-dev python -m app.bootstrap "Casa" "Nome:email@exemplo.com"
docker compose logs -f backend
```

O diretório `backend/` é montado em `/app` - mudanças nos arquivos reiniciam o servidor automaticamente.

## Variáveis de Ambiente

### Backend (`backend/.env`)

#### Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | Connection string do PostgreSQL (asyncpg) | `postgresql+asyncpg://planna:planna@localhost:5433/planna` |
| `COOKIE_SECRET` | Chave para assinatura dos cookies de sessão. Mínimo 32 caracteres aleatórios | `openssl rand -hex 32` |

#### Aplicação

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `APP_ENV` | Ambiente da aplicação. `production` exige HTTPS, SMTP e METRICS_TOKEN | `development` |
| `FRONTEND_URL` | URL do frontend (usado em CORS e links do magic link) | `http://localhost:3000` |
| `PUBLIC_API_URL` | URL pública da API (usada nos links do e-mail de acesso) | `http://localhost:3000/api` |
| `CORS_ORIGINS` | Lista JSON de origens permitidas pelo CORS | `["http://localhost:3000"]` |
| `TRUSTED_HOSTS` | Lista JSON de hosts aceitos pelo middleware TrustedHost | `["localhost","127.0.0.1"]` |
| `LOG_LEVEL` | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

#### E-mail (SMTP)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `SMTP_HOST` | Servidor SMTP. Se vazio, magic links aparecem no terminal | vazio |
| `SMTP_PORT` | Porta do servidor SMTP | `587` |
| `SMTP_USERNAME` | Usuário para autenticação SMTP | vazio |
| `SMTP_PASSWORD` | Senha para autenticação SMTP | vazio |
| `SMTP_FROM` | Endereço de remetente dos e-mails | `acesso@planna.local` |
| `SMTP_USE_TLS` | Usar STARTTLS na conexão SMTP | `true` |

#### Open Finance (Pluggy)

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `PLUGGY_CLIENT_ID` | Client ID da aplicação no Pluggy | Para usar Open Finance |
| `PLUGGY_CLIENT_SECRET` | Client Secret da aplicação no Pluggy | Para usar Open Finance |
| `PLUGGY_WEBHOOK_URL` | URL pública HTTPS para receber webhooks do Pluggy (aponta para `/webhooks/pluggy`) | Para sync automático |
| `PLUGGY_WEBHOOK_SECRET` | Segredo compartilhado para validar webhooks. Mínimo 32 caracteres | Para sync automático |

Sem essas variáveis, o restante do painel funciona normalmente. A ação de conectar instituição informa que a integração não está configurada.

#### Insights por IA (OpenAI)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENAI_API_KEY` | Chave da API OpenAI. Se vazia, insights são gerados localmente sem reescrita | vazio |
| `OPENAI_MODEL` | Modelo a utilizar | `gpt-5-mini` |
| `OPENAI_INPUT_COST_PER_MILLION` | Custo por 1M tokens de entrada (para rastreio de custo) | `0` |
| `OPENAI_OUTPUT_COST_PER_MILLION` | Custo por 1M tokens de saída (para rastreio de custo) | `0` |

O envio de dados para a OpenAI depende do consentimento de **todos** os membros do household. O payload contém apenas sinais financeiros agregados, sem dados pessoais ou transações individuais.

#### Operações

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `METRICS_TOKEN` | Token para acessar `GET /operations/metrics`. Mínimo 32 caracteres. Obrigatório em produção | vazio |

### Frontend (`frontend/.env.local`)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `API_URL` | URL do backend | `http://127.0.0.1:8010` |

## Endpoints de Operação

| Endpoint | Descrição | Autenticação |
|----------|-----------|-------------|
| `GET /health` | Liveness check | Nenhuma |
| `GET /ready` | Readiness check (verifica conexão com PostgreSQL) | Nenhuma |
| `GET /operations/metrics?days=30` | Métricas de sync e uso/custo de IA | Header `X-Metrics-Token` |

## Notas Fiscais

No painel autenticado, cole o link da NFC-e ou fotografe o QR code. A API:

1. Faz parsing da nota via SEFAZ (suporte a NFC-e de Alagoas)
2. Persiste a nota e seus itens, evitando duplicatas pela chave de acesso
3. Procura uma transação Pluggy de mesmo valor entre a emissão e os dois dias seguintes
4. Se encontra correspondência, concilia com a transação bancária
5. Se não encontra, registra como compra via vale-alimentação no extrato

## Backup

Para backup diário com retenção de 30 dias (padrão):

```bash
docker compose --profile production up -d postgres backup
```

Os dumps ficam em `backups/`. A retenção pode ser alterada via `BACKUP_RETENTION_DAYS`.

Para restaurar:

```bash
pg_restore --clean --if-exists --dbname <destino> backups/<arquivo>.dump
```

Em produção, armazene o diretório `backups/` em disco criptografado e teste a restauração periodicamente.

## Verificação

```bash
# Backend - lint e testes
cd backend && uv run ruff check . && uv run pytest

# Frontend - lint e build
cd frontend && npm run lint && npm run build
```

## Estrutura do Projeto

```
planna/
  backend/
    app/
      main.py          # FastAPI app, middlewares, routers
      auth.py           # Magic link, sessões, autenticação
      bootstrap.py      # Seed de household e membros
      config.py         # Settings via pydantic-settings
      database.py       # Engine e sessão async
      models.py         # SQLAlchemy models
      schemas.py        # Pydantic schemas (request/response)
      finance.py        # Contas, transações, KPIs, trends, sync Pluggy
      invoices.py       # Ingestão e conciliação de NFC-e
      wealth.py         # Patrimônio, ativos, passivos, net worth
      insights.py       # Sinais determinísticos + narrativa por IA
      pluggy.py         # Client HTTP para API Pluggy
      sefaz.py          # Parser de NFC-e via SEFAZ
      operations.py     # Métricas operacionais
      security.py       # CSRF, cookies
    alembic/            # Migrations
    tests/
  frontend/
    src/
      app/              # Next.js app router (pages, layout)
      components/       # React components (dashboard, insights, wealth, invoices)
      api.ts            # Client HTTP para o backend
  ops/
    backup.sh           # Script de backup do PostgreSQL
  docker-compose.yml
```
