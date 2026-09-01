# Decisions

Append-only log of architecture decisions. One entry per decision, newest at the bottom. Don't edit past entries — a reversed decision gets a new entry that supersedes the old one, rather than an edit.

## 2026-08-31 — Record architecture decisions

**Status:** Accepted

**Context:** We need a lightweight way to record why significant technical decisions were made, so future work — by any contributor, human or AI, in any tool — doesn't rediscover or accidentally reverse them without knowing the original reasoning.

**Decision:** We will keep architecture decisions in `docs/decisions.md`, one entry per decision, appended chronologically. Entries are append-only — a changed decision gets a new entry that supersedes the old one, rather than an edit.

**Consequences:** Decisions and their reasoning survive context resets, tool switches, and contributor turnover.

## 2026-08-31 — Build MVP around automated external job discovery

**Status:** Accepted

**Context:** The product has no utility if the user must manually find jobs and paste descriptions. The core product value is discovering jobs she would otherwise miss and reducing manual browsing.

**Decision:** The MVP will include automated external job discovery from public/ATS/company sources from day one. Manual job input is not the primary MVP path. See `docs/specs/pookie-employer.md` for full product requirements.

**Consequences:** Crawling/source coverage, deduplication, source observability, and legal/ToS-safe ingestion become core architecture concerns, not optional future enhancements.

## 2026-08-31 — Treat profile and job-search data as sensitive

**Status:** Accepted

**Context:** Resume data, salary preferences, work authorization constraints, employment history, and recommendation feedback are sensitive personal information.

**Decision:** If hosted, the app must use real authentication and minimize stored sensitive data. AI-generated profile fields, inferred preferences, hard filters, and source expansion changes require confirmation before affecting matching or crawling. See `docs/specs/pookie-employer.md` for full context.

**Consequences:** Authentication, data deletion/export, consent for third-party AI use, and privacy-conscious storage must be addressed during technical design.

## 2026-08-31 — Use a TypeScript Next.js/PostgreSQL MVP architecture

**Status:** Accepted

**Context:** The project needs a small full-stack app with a dashboard, authenticated API actions, persistent job/source/run data, and scheduled ingestion. There is no existing code or stack to preserve.

**Decision:** The MVP will use TypeScript on Node.js, Next.js App Router, Tailwind CSS, PostgreSQL, and Prisma. Scheduling starts as protected cron/on-demand endpoints and can move to a queue-backed worker only when measured crawl duration requires it. See `docs/designs/2026-08-31-pookie-employer.md` for full design context.

**Consequences:** `AGENTS.md` now records npm/Next.js commands. Early implementation can stay in one small app while preserving clear service boundaries for ingestion, ranking, AI calls, and dashboard actions.

## 2026-08-31 — Require explicit consent before third-party AI matching

**Status:** Accepted

**Context:** AI matching may send resume-derived profile data and job preferences to an external provider. The product spec allows third-party AI only with explicit consent.

**Decision:** The app must record explicit user/profile consent and allowed provider/model family before third-party AI calls are used for matching or summaries. Full prompts/responses containing sensitive data should not be stored by default. See `docs/designs/2026-08-31-pookie-employer.md` for privacy details.

**Consequences:** Onboarding/profile setup must include AI consent before the real MVP uses hosted LLM APIs. The first hardcoded-profile milestone must still treat provider choice and prompt logging as privacy-sensitive.

## 2026-08-31 — Split dashboard frontend from FastAPI ingestion/ranking backend

**Status:** Accepted

**Context:** The earlier Next.js-only design kept ingestion and ranking on server-side routes, not in the browser, but still coupled the dashboard app to long-running crawl/rank work. The MVP's core value depends on backend-heavy ingestion, parsing, AI evaluation, retries, and observability. Python also offers broader AI, scraping, parsing, and data-processing libraries.

**Decision:** Supersede the earlier single Next.js/PostgreSQL architecture. The MVP will use a Next.js/TypeScript frontend for the dashboard and a dedicated Python FastAPI backend for APIs, ingestion, normalization, deduplication, AI ranking, cron/CLI jobs, and source observability. PostgreSQL remains the shared persistence layer, managed through SQLAlchemy 2.x and Alembic on the backend. See `docs/designs/2026-08-31-pookie-employer.md` for the revised design.

**Consequences:** The implementation has two services from the start, which adds setup overhead but creates a clearer boundary for the product's long-running backend work and AI tooling. `AGENTS.md` now records separate frontend/backend stack expectations; exact commands remain TBD until scaffolding.

## 2026-08-31 — Backend owns domain data and AI pipeline boundaries

**Status:** Accepted

**Context:** Splitting the frontend and backend improves fit for ingestion/ranking work, but it introduces cross-service auth, API contract, data ownership, and deployment risks.

**Decision:** The FastAPI backend is the sole owner of domain database writes, SQLAlchemy/Alembic migrations, ingestion/ranking execution, AI provider integration, API authorization, and sensitive domain logic. The Next.js frontend owns presentation and user interaction only, calling documented backend REST APIs. FastAPI OpenAPI is the API contract source. See `docs/designs/2026-08-31-pookie-employer.md` for the boundary matrix.

**Consequences:** Implementation tasks should avoid direct frontend database access and duplicated business rules. Auth/CORS/API-contract setup becomes an early foundation task before dashboard and backend work proceed in parallel.

## 2026-08-31 — Start with on-demand refresh and defer daily scheduling

**Status:** Accepted

**Context:** The app is for one user and should keep early infrastructure and AI costs low. Daily scheduled crawling may spend money when nobody is using the app and adds deployment/scheduler complexity before recommendation quality is proven. The main UX concern with on-demand refresh is avoiding long waits.

**Decision:** The first milestone will use on-demand refresh only. Refresh should target completion within 90 seconds for the approved source set by using bounded concurrency, strict per-source/total timeouts, unchanged-job skipping, deterministic filtering before AI, AI evaluation caps, partial results, and visible refresh status. Daily scheduled refresh is deferred until on-demand results prove useful and the user wants proactive updates.

**Consequences:** Deployment no longer needs a production scheduler for the first milestone. Backend crawl/rank endpoints and tasks should be framed around on-demand refresh/status. Debug/coverage UI must show elapsed time, failed/slow sources, pending evaluations, and partial results so the user is not blocked by slow sources.

## 2026-08-31 — Deploy as monorepo services with managed durable Postgres

**Status:** Accepted

**Context:** The current `localhost` Postgres is only for local development. The user needs a durable production store and simple deployment path without splitting the GitHub repository.

**Decision:** Keep the monorepo. Deploy the Next.js frontend from `frontend/` and the FastAPI backend from `backend/` as separate services. Use managed PostgreSQL for production durability. Vercel is preferred for the frontend; Railway or Render are acceptable for the backend and managed Postgres, with Railway likely simplest for early MVP. Local Docker Postgres remains development-only.

**Consequences:** Production environment variables must point at managed services, not localhost. Deployment docs must cover frontend origin/CORS, backend URL/secrets, managed `DATABASE_URL`, AI keys when approved, and the on-demand refresh flow. Free/trial tiers may be used for development, but any ephemeral/free database must not be treated as durable production storage.
