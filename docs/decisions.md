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

## 2026-09-01 — Seed sources with application-level idempotency keys

**Status:** Accepted

**Context:** The initial seed command needs to be safe to rerun without creating duplicate profile or source rows, but the current schema does not define a unique constraint for `job_sources`.

**Decision:** The seed command will use `owner_user_id` as the natural idempotency key for the profile and a lookup-before-insert pattern keyed on `(kind, company_name, external_board_id)` for each source. No new migration is added for this task.

**Consequences:** Seeding remains simple and reversible while preserving repeated-run safety. If source identity rules change later, the seed logic will need to be updated in tandem with any future uniqueness constraint.

## 2026-09-08 — Eligibility role gate requires an explicit software-title match

**Status:** Accepted

**Context:** The original allowlist matched generic terms (`\bengineer`, `\bdeveloper`, `\bplatform`, `\binfrastructure`), which let non-software-engineering roles through refresh filtering: "Senior Product Manager - Observability Data Platform" (matched `platform`), "Senior Data Engineer" (matched `engineer`), and "Engineering Compensation Partner" (`\bengineer` prefix-matches "Engineering").

**Decision:** A title passes the role gate only if it pairs `software` with `engineer`/`developer`, or matches a core software-family phrase adjacent to engineer/developer (backend, frontend, full stack, devops, site reliability, SDE/SWE/SRE abbreviations). A stricter "must literally contain software" variant was rejected: it would also filter classic software titles like "Backend Engineer", "Frontend Engineer", and "DevOps Engineer". The non-engineering override list is kept as a second layer for gate-passing compounds like "Software Sales Engineer".

**Consequences:** Data/security/platform/infrastructure engineering roles are filtered deterministically before AI evaluation. Management and specialty titles that no longer pass the role gate report `not_engineering_role` instead of `seniority_too_high`/`non_engineering_specialty`. `make backfill` exists to re-apply future filter changes to stored jobs without AI calls.

## 2026-09-08 — Senior, DevOps, and SRE titles excluded from results

**Status:** Accepted — supersedes the role-family scope of "Eligibility role gate requires an explicit software-title match" (same day), which kept the devops/SRE family and allowed Senior titles.

**Context:** Live-results review surfaced "DevOps Engineer (Observability)" and Senior-titled roles the user does not want. The profile is targeting individual-contributor software product roles (backend/frontend/full-stack), not infrastructure/operations or Senior-level positions.

**Decision:** `\bsenior\b` moved into `_OVER_SENIOR_PATTERNS` (seniority ceiling is now below Senior). DevOps and SRE/site-reliability removed from `_CORE_SOFTWARE_PATTERNS`; bare DevOps/SRE titles fail the role gate (`not_engineering_role`), and `\bdevops\b`, `\bsre\b`, `\bsite reliability\b` were added to `_NON_ENGINEERING_OVERRIDES` so gate-passing compounds (e.g. "Software DevOps Engineer") report `non_engineering_specialty`. The stricter "must literally contain software" variant remains rejected — "Backend Engineer" and "Frontend Engineer" still pass.

**Consequences:** DevOps/SRE/infra-adjacent and all Senior+ IC roles are filtered before AI evaluation; stored jobs re-filtered via `make backfill` (3,188 of 3,262 filtered, 74 visible). If the user later wants DevOps or Senior roles back, re-adding the core patterns and rerunning the backfill restores them (0 restored in the last run means filtered jobs are recoverable, not deleted).

## 2026-09-08 — Cover remaining target companies with direct adapters; paid aggregator rejected

**Status:** Accepted (T45 research; see docs/designs/2026-09-08-remaining-companies-adapters.md)

**Context:** 16 target companies have no source. T45 originally assumed an aggregator adapter (e.g. SerpApi Google Jobs, ~$75/mo for 5k searches). Probing on 2026-09-08 showed Databricks and MongoDB are on Greenhouse (existing adapter), Adobe is on Phenom People (same platform family as the Netflix adapter), Amazon and Apple expose reachable listing APIs, and the rest need dev-machine verification because plain fetches are bot-blocked.

**Decision:** Option A — direct per-company/ATS adapters, no recurring paid dependency. Databricks + MongoDB seed via the existing Greenhouse adapter (T45); a Phenom adapter clones the Netflix pattern for Adobe (T46/T48); dedicated adapters for Amazon `search.json` (T50) and Apple `role/search` (T51), seeded together (T52); remaining backends verified from a dev machine before more adapter tasks (T49). SerpApi, free aggregators (Adzuna/The Muse), and headless-browser scraping are all rejected for now.

**Consequences:** Best data quality (official postings, stable apply URLs, clean dedupe) at the cost of building/maintaining one adapter per company/ATS. Google (no public API) and scraper-hostile sites (X, Bloomberg) stay uncovered unless the user later approves scraping or reconsiders an aggregator. Adapter tasks are serialized (each adds a SourceKind enum value + migration + dispatch branch + frontend union value in the same files).

## 2026-09-08 — Amazon dropped from the target company list

**Status:** Accepted (amends "Cover remaining target companies with direct adapters", same day)

**Context:** The T45 research plan included a dedicated Amazon adapter (planned as T50) built on the verified `amazon.jobs/en/search.json` API.

**Decision:** The user removed Amazon from the target list before the task started. T50's id is retired and never reused; the remaining chain is T46 (Phenom adapter) → T48 (seed Adobe), T46 → T51 (Apple adapter) → T52 (seed Apple), with T45 (Greenhouse seeds) and T49 (backend verification) parallel-ready.

**Consequences:** Amazon postings will not appear in the dashboard. The probing findings stay in the research doc, so re-adding Amazon later is just a new adapter/seed task.
