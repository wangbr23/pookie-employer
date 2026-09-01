# Pookie Employer

AI job finder for a software engineer that discovers external jobs, ranks them against her experience/preferences, and presents recommendations in a dashboard.

## Repository layout

This repo is intentionally split into two services:

- `frontend/` — Next.js + TypeScript + Tailwind dashboard. Owns presentation, routing, and user interactions.
- `backend/` — Python + FastAPI service. Owns API authorization, domain database writes, ingestion, normalization, dedupe, AI ranking, cron/CLI jobs, and source observability.

The frontend must not write directly to the database or implement crawler/ranker logic. It should call documented backend APIs once those exist.

## Current state

The frontend and backend scaffolds exist. Product behavior has not been implemented yet.

## Local PostgreSQL development environment

The backend requires PostgreSQL for persistence. For local development, you can start a PostgreSQL instance using Docker Compose:

```bash
docker-compose up -d postgres
```

This will start PostgreSQL 15 on port 5432 with default credentials (`postgres:postgres`). The database `pookie_employer_dev` will be created automatically.

### Alternative: Homebrew PostgreSQL

If you prefer a locally installed PostgreSQL server:

```bash
brew install postgresql
brew services start postgresql
createdb pookie_employer_dev
```

Adjust the `DATABASE_URL` in your `.env` accordingly (e.g., `postgresql://localhost:5432/pookie_employer_dev`).

Connection configuration is templated in `.env.example`. Copy it to `.env` and adjust the `DATABASE_URL` as needed.

```bash
cp .env.example .env
```

**Important:** Never commit `.env` or any file containing secrets. The `.env` file is git‑ignored.

## Development notes

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run typecheck
npm run build
```

Frontend tests are not configured yet.

### Backend

```bash
cd backend
make dev
make run
make test
make lint
make typecheck
make format
```

### Repository shape

```text
frontend/   # Next.js dashboard app
backend/    # FastAPI backend and worker/job code
docs/       # specs, designs, decisions, and journal
```

See `AGENTS.md` for project context and `docs/designs/2026-08-31-pookie-employer.md` for the implementation design.
