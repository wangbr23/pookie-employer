# Journal

Append-only. One entry per work session. Newest at the bottom. Don't edit past entries — if something's wrong now, say so in a new entry.

## 2026-08-31 — project created

Initialized project scaffold (AGENTS.md, CLAUDE.md, CLEANCODE.md, docs/specs, docs/designs, decisions log, TODO, .pi/skills). Nothing built yet.

## 2026-08-31 — product grilling completed

Grilled and saved the Pookie Employer product spec at `docs/specs/pookie-employer.md`. Key outcomes: automated external job discovery is required from day one, MVP is a read-only recommender/dashboard, and sensitive profile/job-search data must be handled carefully. Next step is technical design review.

## 2026-08-31 — design review completed

Drafted and reviewed the implementation design at `docs/designs/2026-08-31-pookie-employer.md` using two DeepSeek R1 read-only reviewer runs. Accepted revisions around AI consent, privacy, uncertainty fields, cost/crawl monitoring, cron-to-queue migration triggers, and usefulness metrics. Updated `AGENTS.md` with the chosen TypeScript/Next.js/PostgreSQL stack.

## 2026-08-31 — design revised for FastAPI backend

After user feedback, revised the design away from a single Next.js server-side architecture. The design now uses a Next.js/TypeScript dashboard frontend plus a dedicated Python FastAPI backend for ingestion, ranking, AI integration, cron/CLI jobs, and APIs. Updated `AGENTS.md` and `docs/decisions.md` accordingly.

## 2026-08-31 — cross-service boundary patch

Patched `docs/designs/2026-08-31-pookie-employer.md` after an additional DeepSeek R1 review. Added explicit frontend/backend ownership, API contract, auth options, CORS, logging/error, migration, and API drift guidance. Recorded the backend data/API ownership decision in `docs/decisions.md`.

## 2026-08-31 — T1 repo structure scaffolded

Completed `T1`: added `frontend/` and `backend/` directories with responsibility READMEs, added root `README.md` explaining the two-service layout, and expanded `.gitignore` for common Node, Python, environment, cache, OS, and editor artifacts. No product behavior was implemented.

## 2026-08-31 — T2-T4 merged

Merged reviewed scaffold branches for `T2`, `T3`, and `T4` into `main`: Next.js/Tailwind frontend scaffold, FastAPI backend scaffold with health/test/tooling setup, and local PostgreSQL Docker Compose/env documentation. Marked all three tasks complete in `TODO.md`.

## 2026-08-31 — T5 commands and conventions updated

Completed `T5`: updated `AGENTS.md` with concrete frontend/backend install, dev, lint/typecheck, test, format, and build commands from the scaffolds. Added repo-specific service-boundary, API-contract, and testing conventions to `CLEANCODE.md`. Updated root `README.md` development notes to match the current scaffold state.

## 2026-08-31 — T6 backend config and database layer

Completed `T6`: added typed FastAPI settings loaded from environment, SQLAlchemy engine/session setup for PostgreSQL, safe database URL redaction, dependency updates, backend configuration documentation, and pytest coverage for config/database initialization and secret redaction.

## 2026-08-31 — on-demand refresh and deployment plan update

Updated the design and tasks to make on-demand refresh the first-milestone behavior, with daily scheduling deferred. Added a 90-second refresh budget strategy using bounded source concurrency, per-source and total timeouts, unchanged-job skipping, AI evaluation caps, partial results, and refresh status. Added deployment guidance: keep the monorepo, deploy the Next.js frontend from `frontend/`, deploy the FastAPI backend from `backend/`, and use managed PostgreSQL for durable production storage instead of local Docker Postgres.

## 2026-08-31 — T7 schema work split

Split the original broad `T7` schema task into smaller reviewable chunks: Alembic framework setup (`T7`), core profile/source/crawl schema (`T36`), and job recommendation/feedback schema (`T37`). Updated downstream task dependencies to depend on the specific schema layer they need.

## 2026-09-01 — T7 merged

Reviewed and merged the Alembic migration framework. Backend checks passed: 10 tests, Ruff, and mypy. The T7 worktree was cleaned up after merge.

## 2026-09-01 — T7 migration workflow completed

Follow-up verification found that T7 was marked complete without a tracked `alembic/versions/` directory, and its current-command test accepted missing-path errors. Added the versions directory with a no-op `0001_bootstrap` revision and tests that verify the revision graph via `alembic heads`. Domain schema revisions remain deferred to T36/T37.

## 2026-09-01 — T36 schema implementation in progress

Added SQLAlchemy models and the `0002_core_ingestion_schema` Alembic revision for user profiles, job sources, crawl runs, source runs, and raw job postings, including explicit status enums, foreign keys, uniqueness constraints, and ingestion indexes. Static checks pass; runtime tests and fresh-database migration validation remain pending because the local backend virtual environment lacks Alembic and its dependency installation is currently hanging.

## 2026-09-01 — T36 completed

Finished T36 after repairing validation in an isolated Python 3.13 environment. All 15 backend tests, Ruff, and mypy pass; Alembic reports `0002_core_ingestion_schema` as the head; offline upgrade SQL generates successfully with all six enum types emitted once. A live fresh-PostgreSQL upgrade could not be run because no local PostgreSQL server is available.
