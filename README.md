# Planna

Fundação do painel financeiro doméstico: FastAPI, PostgreSQL/Alembic, autenticação por magic link, household compartilhado e Next.js PWA.

## Executar localmente

Requisitos: Docker, Python 3.11+, uv, Node.js e npm.

```bash
docker compose up -d postgres

cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.bootstrap "Casa" "Pessoa 1:pessoa1@example.com" "Pessoa 2:pessoa2@example.com"
uv run fastapi dev --port 8010
```

Sem SMTP configurado, o link de acesso aparece no terminal do backend apenas em desenvolvimento.

Em outro terminal:

```bash
cd frontend
cp .env.example .env.local
npm run dev
```

Abra `http://localhost:3000`. A API fica disponível em `http://localhost:8010/docs` e é acessada pelo frontend por `/api`.

## Verificar

```bash
cd backend && uv run ruff check . && uv run pytest
cd frontend && npm run lint && npm run build
```
