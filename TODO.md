# TODO

Current and near-term work. Mutable — edit freely, unlike the journal or decisions log.

Task format: `- [ ] \`T<n>\` <description> — <manual|agent>[, depends-on: T<a>, T<b>]`. IDs are sequential and never reused. A task is safe to hand to a parallel agent once every id in its `depends-on` is checked off. See the `plan-tasks` skill.

## Foundation

- [x] `T1` Scaffold root repo structure for separate frontend and backend services — agent, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: repo has clear `frontend/` and `backend/` directories, root README/dev notes explain the two-service layout, root `.gitignore` covers common Node/Python/env artifacts, and no product behavior is implemented.
- [x] `T2` Scaffold Next.js/Tailwind frontend app only — agent, depends-on: T1, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: `frontend/` contains a Next.js App Router TypeScript app with Tailwind configured, the default page runs locally, and frontend install/dev/lint/build commands are documented.
- [x] `T3` Scaffold FastAPI backend app only — agent, depends-on: T1, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: `backend/` contains a Python 3.12+ FastAPI app with dependency management, `/health` route, pytest setup, lint/typecheck tooling, and backend install/dev/test commands documented.
- [x] `T4` Add local PostgreSQL development environment — agent, depends-on: T1, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: local Postgres can be started with a documented command, connection env vars are templated without secrets, and neither frontend nor backend contains hardcoded credentials.
- [x] `T5` Update project commands and conventions after scaffolding — agent, depends-on: T2, T3, T4, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: `AGENTS.md` lists actual install/dev/test/lint/typecheck/build commands for frontend and backend, and `CLEANCODE.md` has any concrete repo-specific conventions discovered during scaffolding.

## Backend data foundation

- [x] `T6` Add backend configuration and database connection layer — agent, depends-on: T3, T4, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: FastAPI loads typed settings from environment, validates required config at startup/test time, connects to Postgres through SQLAlchemy, and tests cover config/database initialization without leaking secrets.
- [x] `T7` Add Alembic migration framework only — agent, depends-on: T6, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend has Alembic installed/configured, migration commands documented, Alembic imports backend settings/database metadata, and an empty/no-op migration workflow can run without defining domain tables yet.
- [x] `T36` Add core profile/source/crawl schema migration — agent, depends-on: T7, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: SQLAlchemy models and one Alembic migration cover user profile, job sources, crawl runs, source runs, and raw job postings with explicit enums and indexes needed for ingestion; migration applies cleanly on a fresh database.
- [x] `T37` Add job recommendation and feedback schema migration — agent, depends-on: T36, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: SQLAlchemy models and one Alembic migration cover canonical jobs, job links, job evaluations, and job feedback with explicit enums for job status, link status, fit buckets, uncertainty, and feedback actions; migration applies cleanly after `T36`.
- [x] `T8` Seed one profile and initial approved source list — agent, complexity: simple, depends-on: T36, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend has a documented seed command that creates one admin-configured profile and a small approved source list without duplicating rows on repeated runs.

## Backend API and security boundary

- [x] `T9` Add backend auth/CORS/request-id foundation — agent, complexity: complex, depends-on: T6, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: FastAPI rejects unauthenticated protected routes, supports the chosen MVP auth pattern via environment config, restricts CORS to configured origins, attaches request IDs to responses/logs, and tests cover allowed/blocked access.
- [x] `T10` Add read-only jobs and coverage API contracts with placeholder data — agent, depends-on: T37, T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: FastAPI exposes documented OpenAPI endpoints for job list, job detail, and debug coverage using database-backed or seeded placeholder data, with Pydantic response schemas matching the design.
- [ ] `T11` Add job feedback API endpoints only — agent, depends-on: T37, T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: save, dismiss, and seen endpoints update job state/feedback with validation and authorization, tests cover valid and invalid transitions, and no frontend UI is changed.
- [ ] `T12` Add protected on-demand refresh/rank trigger API stubs only — agent, depends-on: T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: protected backend endpoints/CLI entrypoints exist for on-demand refresh, refresh status/result, and rerank; they create or report stub run records safely; daily scheduling, real source adapters, and AI ranking are not implemented in this task.

## Ingestion pipeline

- [x] `T13` Implement raw posting persistence and crawl run recording helpers — agent, complexity: complex, depends-on: T36, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend services can create crawl/source runs, upsert raw postings by source/content identity, record counts/errors, and tests cover partial source success/failure bookkeeping.
- [ ] `T14` Implement Greenhouse source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Greenhouse sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [ ] `T15` Implement Lever source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Lever sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [ ] `T16` Implement Ashby source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Ashby sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [ ] `T17` Wire bounded on-demand refresh orchestration across approved sources — agent, depends-on: T12, T14, T15, T16, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: on-demand refresh invokes approved source adapters with bounded concurrency, per-source timeouts, and a total crawl budget; records aggregate/per-source counts, elapsed time, slow/failed sources, and partial success; tests cover mixed success/failure and timeout behavior.

## Normalization, dedupe, and ranking

- [ ] `T18` Implement deterministic normalization and minimum-field validation — agent, depends-on: T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: raw postings can be normalized into job candidates with title/company/location/apply link checks, missing salary/remote uncertainty is represented, and tests cover accepted/rejected/Needs Review cases.
- [ ] `T19` Implement conservative dedupe and job/link upsert — agent, depends-on: T18, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: normalized candidates upsert canonical jobs and job links, obvious duplicates merge while preserving links, uncertain duplicates remain separate, and tests cover repeated crawl idempotency.
- [x] `T20` Add AI provider interface and consent/cost metadata model — agent, complexity: complex, depends-on: T37, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend has a typed AI service interface, profile-level third-party AI consent/provider fields or equivalent storage, AI call metadata/cost recording primitives, and tests prove AI calls are blocked without consent.
- [ ] `T21` Implement job evaluation pipeline with a mock AI provider — agent, depends-on: T19, T20, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend can evaluate jobs into fit buckets, summaries, concerns, uncertainty fields, and internal scores using a deterministic mock provider; dashboard APIs read stored evaluations; no real AI provider is required.
- [ ] `T22` Integrate one real AI provider behind the backend interface — manual, depends-on: T20, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: provider choice, API key, allowed model family, consent posture, and monthly soft budget are approved and available locally without committing secrets.
- [ ] `T23` Enable real AI-backed job evaluation — agent, depends-on: T21, T22, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend can switch from mock to real provider via configuration, stores no full sensitive prompts/responses by default, records call counts/estimated cost, and tests mock external calls.

## Frontend dashboard

- [x] `T24` Build static dashboard shell from mock — agent, complexity: simple, depends-on: T2, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend has the warm sidebar/layout/card styling inspired by `docs/specs/mocks/mock.png`, uses static mock software-engineering job data, and includes no backend integration.
- [ ] `T25` Add frontend API client and authenticated backend fetch setup — agent, depends-on: T10, T24, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend has a small typed API client based on the backend OpenAPI/contracts, handles auth/proxy configuration, and can fetch placeholder jobs from FastAPI in local dev.
- [ ] `T26` Implement For You and All Jobs views with backend data — agent, depends-on: T21, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: dashboard shows new jobs grouped by fit bucket, supports all active jobs view, filter/search basics, old jobs remain accessible, and page load uses stored evaluations rather than live AI calls.
- [ ] `T27` Implement Saved and Archived/Possibly Closed views — agent, depends-on: T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend routes show saved jobs, dismissed/archived jobs, and possibly-closed jobs using backend data, with empty/loading/error states.
- [ ] `T28` Wire save, dismiss, seen, and apply-link interactions — agent, depends-on: T11, T26, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: job cards can save, dismiss with structured reason, mark seen as appropriate, and open preserved apply links; backend state changes are reflected in the UI.
- [ ] `T29` Build refresh status and debug/coverage view — agent, depends-on: T10, T17, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend provides a Refresh jobs action, shows refresh status/result, and the debug page shows last refresh time, source statuses, counts, errors, elapsed time, AI call count/cost when available, pending evaluations, and partial-failure states.

## Operations and data controls

- [ ] `T30` Add export saved jobs endpoint and UI affordance — agent, depends-on: T9, T27, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: authenticated user can export saved jobs as CSV or JSON, export includes apply links and fit summaries, and tests cover authorization.
- [ ] `T31` Add destructive data deletion endpoints only — agent, depends-on: T9, T37, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend supports protected deletion of profile-derived data and job feedback/history with tests; frontend UI is not included in this task.
- [ ] `T32` Add frontend data deletion controls — agent, depends-on: T31, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend exposes clearly labeled deletion controls with confirmation, calls backend deletion endpoints, and handles success/error states.
- [ ] `T33` Select and document MVP deployment plan — manual, depends-on: T5, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend hosting, backend hosting, managed Postgres provider, durability expectations, required production secrets, and on-demand refresh deployment flow are selected/documented without committing secrets. Daily scheduled refresh remains explicitly deferred.
- [ ] `T34` Add production-readiness smoke checks — agent, depends-on: T5, T17, T23, T29, T30, T32, T33, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: documented smoke checklist verifies frontend/backend startup, managed Postgres connectivity, authenticated dashboard access, on-demand refresh under the configured 90-second budget, ranking run, debug coverage, save/dismiss, export, and deletion flows in a deployed or deployment-like environment.

## Follow-up after first milestone

- [ ] `T35` Design onboarding/profile editing follow-up before implementation — manual, depends-on: T34, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: resume upload, extraction, confirmation/editing, raw resume retention, and AI consent UX are reviewed against the spec and either added to a new design patch or explicitly deferred.
