# TODO

Current and near-term work. Mutable — edit freely, unlike the journal or decisions log.

Task format: `- [ ] \`T<n>\` <description> — <manual|agent>[, depends-on: T<a>, T<b>]`. IDs are sequential and never reused. A task is safe to hand to a parallel agent once every id in its `depends-on` is checked off. See the `plan-tasks` skill.

## Foundation

- [x] `T1` Scaffold root repo structure for separate frontend and backend services — agent, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: repo has clear `frontend/` and `backend/` directories, root README/dev notes explain the two-service layout, root `.gitignore` covers common Node/Python/env artifacts, and no product behavior is implemented.
- [ ] `T2` Scaffold Next.js/Tailwind frontend app only — agent, depends-on: T1, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: `frontend/` contains a Next.js App Router TypeScript app with Tailwind configured, the default page runs locally, and frontend install/dev/lint/build commands are documented.
- [ ] `T3` Scaffold FastAPI backend app only — agent, depends-on: T1, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: `backend/` contains a Python 3.12+ FastAPI app with dependency management, `/health` route, pytest setup, lint/typecheck tooling, and backend install/dev/test commands documented.
- [ ] `T4` Add local PostgreSQL development environment — agent, depends-on: T1, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: local Postgres can be started with a documented command, connection env vars are templated without secrets, and neither frontend nor backend contains hardcoded credentials.
- [ ] `T5` Update project commands and conventions after scaffolding — agent, depends-on: T2, T3, T4, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: `AGENTS.md` lists actual install/dev/test/lint/typecheck/build commands for frontend and backend, and `CLEANCODE.md` has any concrete repo-specific conventions discovered during scaffolding.

## Backend data foundation

- [ ] `T6` Add backend configuration and database connection layer — agent, depends-on: T3, T4, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: FastAPI loads typed settings from environment, validates required config at startup/test time, connects to Postgres through SQLAlchemy, and tests cover config/database initialization without leaking secrets.
- [ ] `T7` Add Alembic and initial domain schema migration — agent, depends-on: T6, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: SQLAlchemy models and one Alembic migration cover profile, job sources, crawl/source runs, raw postings, jobs, links, evaluations, and feedback with explicit enums for domain states; migration applies cleanly on a fresh database.
- [ ] `T8` Seed one profile and initial approved source list — agent, depends-on: T7, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend has a documented seed command that creates one admin-configured profile and a small approved source list without duplicating rows on repeated runs.

## Backend API and security boundary

- [ ] `T9` Add backend auth/CORS/request-id foundation — agent, depends-on: T6, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: FastAPI rejects unauthenticated protected routes, supports the chosen MVP auth pattern via environment config, restricts CORS to configured origins, attaches request IDs to responses/logs, and tests cover allowed/blocked access.
- [ ] `T10` Add read-only jobs and coverage API contracts with placeholder data — agent, depends-on: T7, T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: FastAPI exposes documented OpenAPI endpoints for job list, job detail, and debug coverage using database-backed or seeded placeholder data, with Pydantic response schemas matching the design.
- [ ] `T11` Add job feedback API endpoints only — agent, depends-on: T7, T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: save, dismiss, and seen endpoints update job state/feedback with validation and authorization, tests cover valid and invalid transitions, and no frontend UI is changed.
- [ ] `T12` Add protected crawl/rank trigger API stubs only — agent, depends-on: T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: protected backend endpoints/CLI entrypoints exist for daily crawl, on-demand crawl, and rerank; they create or report stub run records safely; real source adapters and AI ranking are not implemented in this task.

## Ingestion pipeline

- [ ] `T13` Implement raw posting persistence and crawl run recording helpers — agent, depends-on: T7, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend services can create crawl/source runs, upsert raw postings by source/content identity, record counts/errors, and tests cover partial source success/failure bookkeeping.
- [ ] `T14` Implement Greenhouse source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Greenhouse sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [ ] `T15` Implement Lever source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Lever sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [ ] `T16` Implement Ashby source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Ashby sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [ ] `T17` Wire crawl orchestration across approved sources — agent, depends-on: T12, T14, T15, T16, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: on-demand/daily crawl invokes approved source adapters, records aggregate and per-source counts/errors, returns partial success when some sources fail, and tests cover mixed success/failure.

## Normalization, dedupe, and ranking

- [ ] `T18` Implement deterministic normalization and minimum-field validation — agent, depends-on: T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: raw postings can be normalized into job candidates with title/company/location/apply link checks, missing salary/remote uncertainty is represented, and tests cover accepted/rejected/Needs Review cases.
- [ ] `T19` Implement conservative dedupe and job/link upsert — agent, depends-on: T18, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: normalized candidates upsert canonical jobs and job links, obvious duplicates merge while preserving links, uncertain duplicates remain separate, and tests cover repeated crawl idempotency.
- [ ] `T20` Add AI provider interface and consent/cost metadata model — agent, depends-on: T7, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend has a typed AI service interface, profile-level third-party AI consent/provider fields or equivalent storage, AI call metadata/cost recording primitives, and tests prove AI calls are blocked without consent.
- [ ] `T21` Implement job evaluation pipeline with a mock AI provider — agent, depends-on: T19, T20, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend can evaluate jobs into fit buckets, summaries, concerns, uncertainty fields, and internal scores using a deterministic mock provider; dashboard APIs read stored evaluations; no real AI provider is required.
- [ ] `T22` Integrate one real AI provider behind the backend interface — manual, depends-on: T20, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: provider choice, API key, allowed model family, consent posture, and monthly soft budget are approved and available locally without committing secrets.
- [ ] `T23` Enable real AI-backed job evaluation — agent, depends-on: T21, T22, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend can switch from mock to real provider via configuration, stores no full sensitive prompts/responses by default, records call counts/estimated cost, and tests mock external calls.

## Frontend dashboard

- [ ] `T24` Build static dashboard shell from mock — agent, depends-on: T2, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend has the warm sidebar/layout/card styling inspired by `docs/specs/mocks/mock.png`, uses static mock software-engineering job data, and includes no backend integration.
- [ ] `T25` Add frontend API client and authenticated backend fetch setup — agent, depends-on: T10, T24, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend has a small typed API client based on the backend OpenAPI/contracts, handles auth/proxy configuration, and can fetch placeholder jobs from FastAPI in local dev.
- [ ] `T26` Implement For You and All Jobs views with backend data — agent, depends-on: T21, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: dashboard shows new jobs grouped by fit bucket, supports all active jobs view, filter/search basics, old jobs remain accessible, and page load uses stored evaluations rather than live AI calls.
- [ ] `T27` Implement Saved and Archived/Possibly Closed views — agent, depends-on: T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend routes show saved jobs, dismissed/archived jobs, and possibly-closed jobs using backend data, with empty/loading/error states.
- [ ] `T28` Wire save, dismiss, seen, and apply-link interactions — agent, depends-on: T11, T26, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: job cards can save, dismiss with structured reason, mark seen as appropriate, and open preserved apply links; backend state changes are reflected in the UI.
- [ ] `T29` Build debug/coverage view — agent, depends-on: T10, T17, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend debug page shows last crawl time, source statuses, counts, errors, crawl duration, AI call count/cost when available, and handles partial-failure states.

## Operations and data controls

- [ ] `T30` Add export saved jobs endpoint and UI affordance — agent, depends-on: T9, T27, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: authenticated user can export saved jobs as CSV or JSON, export includes apply links and fit summaries, and tests cover authorization.
- [ ] `T31` Add destructive data deletion endpoints only — agent, depends-on: T9, T7, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend supports protected deletion of profile-derived data and job feedback/history with tests; frontend UI is not included in this task.
- [ ] `T32` Add frontend data deletion controls — agent, depends-on: T31, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend exposes clearly labeled deletion controls with confirmation, calls backend deletion endpoints, and handles success/error states.
- [ ] `T33` Add scheduled crawl deployment documentation — manual, depends-on: T17, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: hosting/scheduler choice is selected, required secrets are available locally, and the daily crawl trigger command/URL is documented without committing secrets.
- [ ] `T34` Add production-readiness smoke checks — agent, depends-on: T5, T17, T23, T29, T30, T32, T33, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: documented smoke checklist verifies frontend/backend startup, authenticated dashboard access, crawl run, ranking run, debug coverage, save/dismiss, export, and deletion flows in a deployed or deployment-like environment.

## Follow-up after first milestone

- [ ] `T35` Design onboarding/profile editing follow-up before implementation — manual, depends-on: T34, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: resume upload, extraction, confirmation/editing, raw resume retention, and AI consent UX are reviewed against the spec and either added to a new design patch or explicitly deferred.
