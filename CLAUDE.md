# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Planna is a multi-user (SaaS) personal finance management application. It provides transaction tracking, credit card purchase management with installments, automatic categorization via KMeans, file import (OFX/CSV/PDF), analytics (Sankey charts, monthly closing, outlier detection), and email notifications.

## Architecture

- **Frontend**: Nuxt 3 + Nuxt UI (Vue 3, Tailwind CSS) — `frontend/`
- **Backend**: FastAPI (Python 3.12+) — `backend/`
- **Database**: PostgreSQL (async via SQLAlchemy 2.0 + asyncpg)
- **ML**: scikit-learn (TF-IDF + KMeans) for auto-categorization
- **Task queue**: APScheduler for scheduled notifications

## Common Commands

### Backend
```bash
cd backend
source .venv/bin/activate

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Lint
ruff check app/
ruff format app/

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend
```bash
cd frontend

# Run dev server
npm run dev

# Build
npm run build

# Type check
npm run typecheck

# Lint
npm run lint
```

### Docker (full stack)
```bash
docker-compose up          # start all services
docker-compose up -d       # detached
docker-compose down        # stop
```

## Backend Structure

```
backend/app/
├── main.py           # FastAPI app, CORS, router registration
├── config.py         # pydantic-settings (env vars)
├── database.py       # SQLAlchemy async engine + session
├── deps.py           # FastAPI dependencies (get_current_user)
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response schemas
├── routers/          # API route modules
│   ├── auth.py       # /api/auth/* (register, login, refresh, me)
│   ├── transactions.py    # /api/transactions CRUD
│   ├── credit_purchases.py # /api/credit-purchases CRUD
│   ├── lookups.py    # /api/accounts, /api/credit-cards, /api/categories
│   ├── settings.py   # /api/settings (user preferences)
│   ├── imports.py    # /api/import/ofx, /api/import/csv
│   ├── analytics.py  # /api/analytics/sankey, monthly-closing, outliers
│   └── categorize.py # /api/categorize (predict + train)
├── services/         # Business logic
│   ├── auth.py       # JWT, password hashing, user management
│   ├── import_service.py  # OFX/CSV parsing
│   └── analytics.py  # Sankey, monthly closing, IQR outlier detection
└── ml/
    └── categorizer.py # KMeans training and prediction pipeline
```

## Frontend Structure

```
frontend/
├── app.vue
├── nuxt.config.ts
├── composables/
│   ├── useApi.ts     # Typed API client with JWT auto-refresh
│   ├── useAuth.ts    # Auth state (login, register, logout, tokens)
│   └── useCurrency.ts # BRL formatting (Intl.NumberFormat)
├── middleware/
│   └── auth.ts       # Route guard for authenticated pages
├── layouts/
│   ├── default.vue   # Main layout with nav bar
│   └── auth.vue      # Centered card layout for login/register
└── pages/
    ├── index.vue     # Dashboard (Sankey, monthly closing)
    ├── login.vue
    ├── register.vue
    ├── transactions.vue
    ├── credit.vue
    ├── import.vue
    ├── categories.vue
    ├── accounts.vue
    └── settings.vue
```

## Key Patterns

- All API routes are prefixed with `/api`
- Auth uses JWT (access + refresh tokens) via Bearer header
- All data is scoped per user (user_id FK on every table)
- Models use UUID primary keys with `UUIDMixin` and `TimestampMixin`
- Frontend composables are auto-imported by Nuxt
- Dark mode is the default theme
- Portuguese UI labels, BRL currency format (`R$ 1.234,56`)
- IQR (Interquartile Range) method for expense outlier detection
- KMeans model is stored per user in `categorization_models` table (serialized with joblib)

## Environment Variables (backend/.env)

```
DATABASE_URL=postgresql+asyncpg://planna:planna@localhost:5432/planna
SECRET_KEY=change-me-in-production
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=true
```
