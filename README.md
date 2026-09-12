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

Como alternativa, execute PostgreSQL e backend com reload automático no Docker:

```bash
cp backend/.env.example backend/.env
docker compose up -d --build backend
docker compose exec backend uv run --frozen --no-dev python -m app.bootstrap "Casa" "Pessoa 1:pessoa1@example.com" "Pessoa 2:pessoa2@example.com"
docker compose logs -f backend
```

O diretório `backend/` é montado em `/app`; mudanças nos arquivos reiniciam o servidor automaticamente.

## Open Finance

Preencha `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` no `backend/.env`. Para receber atualizações automáticas, configure também uma `PLUGGY_WEBHOOK_URL` pública HTTPS apontando para `/webhooks/pluggy` e gere um `PLUGGY_WEBHOOK_SECRET` aleatório com pelo menos 32 caracteres. Sem essas variáveis, o restante do painel continua funcionando e a ação de conectar instituição informa que a integração não está configurada.

## Notas fiscais

No painel autenticado, cole o link da NFC-e de Alagoas ou fotografe o QR code. A API persiste a nota e seus itens, evita duplicidade pela chave de acesso e procura uma transação Pluggy de mesmo valor entre a emissão e os dois dias seguintes. Sem correspondência, a compra entra no extrato e nos indicadores como vale-alimentação.

## Insights financeiros

Configure `OPENAI_API_KEY` no `backend/.env` para usar a OpenAI na redação e priorização dos insights. Sem a chave, os mesmos sinais e recomendações são gerados localmente. A análise usa os 12 meses completos mais recentes, renova o cache no primeiro acesso de cada mês e pode ser recalculada pelo painel.

O envio à OpenAI também depende do consentimento de todos os membros. O payload contém somente sinais calculados e seu contexto mínimo; sem consentimento, o cálculo local continua disponível.

## Endurecimento e operação

Em produção, use URLs HTTPS em `FRONTEND_URL` e `PUBLIC_API_URL`, ajuste `TRUSTED_HOSTS` para o domínio público e gere um `METRICS_TOKEN` aleatório com pelo menos 32 caracteres. A API oferece:

- `GET /health` para liveness;
- `GET /ready` para readiness com verificação do PostgreSQL;
- `GET /operations/metrics?days=30`, protegido pelo header `X-Metrics-Token`, para estado do sync e uso/custo de IA.

Os logs saem em JSON, com identificador e duração por request, sem query string, e-mail ou valores financeiros. O navegador mantém uma cópia offline por usuário dos GETs autenticados; uma troca de usuário ou logout remove a cópia anterior.

Para iniciar o backup diário com retenção padrão de 30 dias:

```bash
docker compose --profile production up -d postgres backup
```

Os dumps ficam em `backups/`. Em produção, armazene esse diretório em disco criptografado e teste periodicamente a restauração com `pg_restore --clean --if-exists --dbname <destino> backups/<arquivo>.dump`.

## Verificar

```bash
cd backend && uv run ruff check . && uv run pytest
cd frontend && npm run lint && npm run build
```
