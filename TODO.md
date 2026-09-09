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
- [x] `T11` Add job feedback API endpoints only — agent, depends-on: T37, T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: save, dismiss, and seen endpoints update job state/feedback with validation and authorization, tests cover valid and invalid transitions, and no frontend UI is changed.
- [x] `T12` Add protected on-demand refresh/rank trigger API stubs only — agent, depends-on: T9, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: protected backend endpoints/CLI entrypoints exist for on-demand refresh, refresh status/result, and rerank; they create or report stub run records safely; daily scheduling, real source adapters, and AI ranking are not implemented in this task.

## Ingestion pipeline

- [x] `T13` Implement raw posting persistence and crawl run recording helpers — agent, complexity: complex, depends-on: T36, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend services can create crawl/source runs, upsert raw postings by source/content identity, record counts/errors, and tests cover partial source success/failure bookkeeping.
- [x] `T14` Implement Greenhouse source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Greenhouse sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [x] `T15` Implement Lever source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Lever sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [x] `T16` Implement Ashby source adapter — agent, depends-on: T8, T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: allowlisted Ashby sources can be fetched into raw postings using fixture-backed tests, source errors are recorded, and no other ATS adapter is included.
- [x] `T17` Wire bounded on-demand refresh orchestration across approved sources — agent, depends-on: T12, T14, T15, T16, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: on-demand refresh invokes approved source adapters with bounded concurrency, per-source timeouts, and a total crawl budget; records aggregate/per-source counts, elapsed time, slow/failed sources, and partial success; tests cover mixed success/failure and timeout behavior.

## Normalization, dedupe, and ranking

- [x] `T18` Implement deterministic normalization and minimum-field validation — agent, depends-on: T13, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: raw postings can be normalized into job candidates with title/company/location/apply link checks, missing salary/remote uncertainty is represented, and tests cover accepted/rejected/Needs Review cases.
- [x] `T19` Implement conservative dedupe and job/link upsert — agent, depends-on: T18, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: normalized candidates upsert canonical jobs and job links, obvious duplicates merge while preserving links, uncertain duplicates remain separate, and tests cover repeated crawl idempotency.
- [x] `T20` Add AI provider interface and consent/cost metadata model — agent, complexity: complex, depends-on: T37, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend has a typed AI service interface, profile-level third-party AI consent/provider fields or equivalent storage, AI call metadata/cost recording primitives, and tests prove AI calls are blocked without consent.
- [x] `T21` Implement job evaluation pipeline with a mock AI provider — agent, depends-on: T19, T20, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend can evaluate jobs into fit buckets, summaries, concerns, uncertainty fields, and internal scores using a deterministic mock provider; dashboard APIs read stored evaluations; no real AI provider is required.
- [x] `T22` Integrate one real AI provider behind the backend interface — manual, depends-on: T20, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: provider choice, API key, allowed model family, consent posture, and monthly soft budget are approved and available locally without committing secrets.
- [x] `T23` Enable real AI-backed job evaluation — agent, depends-on: T21, T22, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend can switch from mock to real provider via configuration, stores no full sensitive prompts/responses by default, records call counts/estimated cost, and tests mock external calls.

## Frontend dashboard

- [x] `T24` Build static dashboard shell from mock — agent, complexity: simple, depends-on: T2, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend has the warm sidebar/layout/card styling inspired by `docs/specs/mocks/mock.png`, uses static mock software-engineering job data, and includes no backend integration.
- [x] `T25` Add frontend API client and authenticated backend fetch setup — agent, depends-on: T10, T24, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend has a small typed API client based on the backend OpenAPI/contracts, handles auth/proxy configuration, and can fetch placeholder jobs from FastAPI in local dev.
- [x] `T26` Implement For You and All Jobs views with backend data — agent, depends-on: T21, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: dashboard shows new jobs grouped by fit bucket, supports all active jobs view, filter/search basics, old jobs remain accessible, and page load uses stored evaluations rather than live AI calls.
- [x] `T27` Implement Saved and Archived/Possibly Closed views — agent, depends-on: T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend routes show saved jobs, dismissed/archived jobs, and possibly-closed jobs using backend data, with empty/loading/error states.
- [x] `T28` Wire save, dismiss, seen, and apply-link interactions — agent, depends-on: T11, T26, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: job cards can save, dismiss with structured reason, mark seen as appropriate, and open preserved apply links; backend state changes are reflected in the UI.
- [x] `T29` Build refresh status and debug/coverage view — agent, depends-on: T10, T17, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend provides a Refresh jobs action, shows refresh status/result, and the debug page shows last refresh time, source statuses, counts, errors, elapsed time, AI call count/cost when available, pending evaluations, and partial-failure states.

## Operations and data controls

- [x] `T30` Add export saved jobs endpoint and UI affordance — agent, depends-on: T9, T27, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: authenticated user can export saved jobs as CSV or JSON, export includes apply links and fit summaries, and tests cover authorization.
- [x] `T31` Add destructive data deletion endpoints only — agent, depends-on: T9, T37, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: backend supports protected deletion of profile-derived data and job feedback/history with tests; frontend UI is not included in this task.
- [x] `T32` Add frontend data deletion controls — agent, depends-on: T31, T25, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend exposes clearly labeled deletion controls with confirmation, calls backend deletion endpoints, and handles success/error states.
- [ ] `T33` Select and document MVP deployment plan — manual, depends-on: T5, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: frontend hosting, backend hosting, managed Postgres provider, durability expectations, required production secrets, and on-demand refresh deployment flow are selected/documented without committing secrets. Daily scheduled refresh remains explicitly deferred.
- [ ] `T34` Add production-readiness smoke checks — agent, depends-on: T5, T17, T23, T29, T30, T32, T33, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: documented smoke checklist verifies frontend/backend startup, managed Postgres connectivity, authenticated dashboard access, on-demand refresh under the configured 90-second budget, ranking run, debug coverage, save/dismiss, export, and deletion flows in a deployed or deployment-like environment.

## Follow-up after first milestone

- [ ] `T35` Design onboarding/profile editing follow-up before implementation — manual, depends-on: T34, design: docs/designs/2026-08-31-pookie-employer.md
  - Done when: resume upload, extraction, confirmation/editing, raw resume retention, and AI consent UX are reviewed against the spec and either added to a new design patch or explicitly deferred.

## Before launch

Discovered during the T22/T23 end-to-end test (2026-09-07): the first live refresh pulled 246 jobs from 5 companies, only ~90 eng-titled, and the 25-per-run evaluation cap spends AI calls on obvious non-fits. These cut AI spend and improve coverage before real use.

- [x] `T38` Curate an expanded approved company/source list across Greenhouse, Lever, and Ashby — manual
  - Done when: a reviewed list of target companies with board kind and board id exists (each board verified reachable), replacing the current 5-company test set.
  - Completed 2026-09-08: 14 companies added via Greenhouse/Ashby (Airbnb, Stripe, Coinbase, Roblox, Discord, Lyft, Asana, Datadog, LinkedIn, Dropbox, Twilio, DoorDash, Snowflake, Notion) plus 4 original smaller companies. 16 remaining companies need new adapters — see T41–T44.
- [x] `T39` Seed the expanded source list and prune dead boards — agent, complexity: simple, depends-on: T38
  - Done when: new sources are seeded idempotently into `job_sources`, each fetches successfully through its adapter, and stale/unreachable boards (e.g. the 404-ing Greenhouse/Lever rows) are paused or removed.
  - Completed 2026-09-08: 18 active approved sources seeded. Stale Lever/Greenhouse dupes from original test set remain paused.
- [x] `T40` Add profile-driven pre-evaluation eligibility filter (software-engineering roles, salary floor, allowed locations, seniority range) — agent, complexity: complex
  - Done when: jobs failing the profile's target role families, salary floor, allowed locations, or seniority min/max skip AI evaluation without spending provider calls; filtered jobs are retained and visible with a skip reason rather than deleted; filter decisions are counted in crawl run reporting; tests cover each criterion and interplay with the evaluation cap.
  - Completed 2026-09-08: eligibility.py filters on 4 criteria (engineering title, seniority below Senior, New York / remote / US-wide location, salary floor $170k). Integrated into evaluate_pending_jobs — filtered jobs are retained in DB but skip AI calls. EvaluationRunCounts.filtered tracks the count. 49 unit tests + 2 integration tests. Profile updated: allowed_locations=["New York, NY"], salary_floor=$170k, seniority_max=5.
  - Updated 2026-09-08 (user review): Senior, DevOps, and SRE/site-reliability titles are now excluded too — seniority ceiling is below Senior; DevOps/SRE removed from the core role patterns and added to the non-engineering overrides. See decisions.md.

## Additional source adapters

Remaining target companies after the Greenhouse/Lever/Ashby/Workday/Netflix adapters. Decision (2026-09-08, T45 research): direct per-company/ATS adapters, no paid aggregator — see docs/designs/2026-09-08-remaining-companies-adapters.md. Adapter tasks are serialized behind T46 because each adds a `SourceKind` enum value + migration + dispatch branch + frontend union value (same files).

- [x] `T41` Implement Workday source adapter — agent, complexity: complex
  - Done when: a Workday adapter can fetch job postings via the `/wday/cxs/{tenant}/{site}/jobs` POST API, parse results into `RawPosting`s, and handle pagination; tested against at least one live Workday board.
  - Covers: NVIDIA (`nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`, 1714 jobs), Salesforce (`salesforce.wd12.myworkdayjobs.com/External_Career_Site`, 526 jobs). Also potentially Adobe and others once their Workday site names are discovered.
  - Completed 2026-09-08: `SourceKind.WORKDAY` + migration 0005 (native enum value). `external_board_id` stores `tenant/site`; host comes from `base_url`. Pages fetched offset-by-offset (page 0's `total` is the only reliable one — later pages answer `total: 0`); known offsets fetched with a 4-way pool because NVIDIA's ~2000 postings take ~96s sequential (~29s pooled). All-or-nothing per-source errors; in-fetch id dedupe for board churn. Live-verified: NVIDIA 1998 postings in 29.2s, Salesforce 1450 in 11.8s, apply URLs return 200. Known limits: list API has no descriptions (postings land in Needs Review; AI snapshot never reads descriptions anyway) and `locationsText` can be a count ("2 Locations") — kept as-is for downstream triage.
- [x] `T42` Implement Netflix source adapter — agent, complexity: medium
  - Done when: a Netflix adapter can fetch job postings via `explore.jobs.netflix.net/api/apply/v2/jobs?domain=netflix.com`, parse results into `RawPosting`s, and handle pagination; tested with fixture data.
  - API confirmed working: ~498 jobs, returns JSON with `positions` array.
  - Completed 2026-09-08: `SourceKind.NETFLIX` + migration 0006. Adapter pages via `start`/`num` — server caps `num` at 10/page regardless of request; page 0's `count` drives the remaining offsets, fetched with a 4-way pool like Workday. Fixture-backed tests plus live verification: 497 postings in 4.2s, all ids unique, apply URLs return 200. Frontend `SourceKind` union also gained the missing `workday` value (T41 drift) plus `netflix`.
- [x] `T43` Add NVIDIA and Salesforce as Workday sources — agent, complexity: simple, depends-on: T41
  - Done when: NVIDIA and Salesforce are seeded as Workday sources, fetch successfully through the Workday adapter, and appear in the dashboard.
  - Completed 2026-09-08: seeded via `seed.py` (20 approved sources, idempotent); live refresh ran 20/20 sources succeeded — NVIDIA 2000 postings inserted, Salesforce 1449 inserted. Eligibility triage: NVIDIA 1632 not_engineering_role / 296 seniority_too_high / 67 location_mismatch / 4 non_engineering_specialty / 1 eligible; Salesforce 1389 / 35 / 22 / 2 / 1 eligible. Both eligible jobs evaluated (needs_review — expected, no descriptions) and verified in the UI: For You → Needs Review shows both cards with Workday apply links; All Jobs search "NVIDIA" returns the eligible job. Refresh took ~15 min end to end (crawl within budget; evaluation phase uncapped — pre-existing known issue).
- [x] `T44` Add Netflix source — agent, complexity: simple, depends-on: T42
  - Done when: Netflix is seeded as a source, fetches successfully through its adapter, and appears in the dashboard.
  - Completed 2026-09-08: seeded via `seed.py` (21 approved sources, idempotent; seed test count bumped to 21 + NETFLIX kind). Live refresh ran 20/21 sources succeeded (Datadog timed out — transient, unrelated); Netflix fetched 496 postings, 494 canonical after dedupe. Eligibility triage: 429 not_engineering_role / 8 location_mismatch / 6 seniority_too_high / 1 non_engineering_specialty / 50 eligible; 25 eligible jobs evaluated in this run's cap (two `strong` fits, rest mostly `needs_review` — Netflix list API supplies no descriptions). Dashboard API returns all 50 eligible Netflix jobs with apply links.
- [x] `T45` Seed Databricks and MongoDB as Greenhouse sources — agent, complexity: simple, design: docs/designs/2026-09-08-remaining-companies-adapters.md
  - Done when: both companies are seeded idempotently via seed.py as Greenhouse sources, fetch through the existing Greenhouse adapter in a live refresh, and appear in the dashboard with apply links.
  - Boards verified reachable 2026-09-08: boards-api.greenhouse.io/databricks, /mongodb.
  - Completed 2026-09-09: added to SEED_SOURCES (23 approved sources; seed test count bumped). Re-verified boards reachable, then live refresh: 23/23 sources succeeded — Databricks 868 postings inserted, MongoDB 406 inserted. Dashboard-visible eligible jobs: Databricks 1, MongoDB 6, all with active apply links (sample: "Sr. Software Engineer- Backend", New York City, needs_review). Note: a first refresh attempt was lost to a rollback (script omitted commit; run_refresh itself never commits) — that run's 25 AI evaluations were spent twice; see decisions on AI spend soft budget and T47 for the cost rollup gap.
- [ ] `T46` Implement Phenom source adapter — agent, complexity: complex, design: docs/designs/2026-09-08-remaining-companies-adapters.md
  - Done when: an adapter clones the Netflix adapter pattern (paginate the `/api/apply/v2/jobs` API), adds `SourceKind.PHENOM` with migration and frontend union value, fixture-backed tests pass, and one live Phenom board (Adobe's tenant) is verified end to end.
  - Adobe confirmed Phenom 2026-09-08 (careers.adobe.com). The tenant/domain request parameter must be discovered during implementation. Spotify/Uber/Shopify are suspected Phenom — verify via T49 before seeding them.
- [ ] `T48` Add Adobe as Phenom source — agent, complexity: simple, depends-on: T45, T46, design: docs/designs/2026-09-08-remaining-companies-adapters.md
  - Done when: Adobe is seeded idempotently via seed.py, fetches successfully through the Phenom adapter in a live refresh, and appears in the dashboard with apply links.
- [ ] `T49` Verify careers-site backends for remaining companies — agent, complexity: simple, design: docs/designs/2026-09-08-remaining-companies-adapters.md
  - Done when: for each of Spotify, Microsoft, Tesla, Uber, Snap, X, Bloomberg, Atlassian, Oracle, Shopify the ATS backend and a working listing API are identified (or confirmed absent) using a real browser network tab or curl from a dev machine — plain fetches are bot-blocked for several — and findings are recorded in the research doc.
- [ ] `T51` Implement Apple source adapter — agent, complexity: complex, depends-on: T46, design: docs/designs/2026-09-08-remaining-companies-adapters.md
  - Done when: an adapter fetches Apple postings via the `jobs.apple.com` JSON API (or server-rendered search page as fallback) with pagination into `RawPosting`s, fixture-backed tests pass, and one live fetch is verified. Descriptions are available — prefer the API path.
- [ ] `T52` Add Apple as a source — agent, complexity: simple, depends-on: T48, T51, design: docs/designs/2026-09-08-remaining-companies-adapters.md
  - Done when: Apple is seeded idempotently via seed.py, fetches successfully through its adapter in a live refresh, and appears in the dashboard with apply links.
  - Note: T50 (Amazon adapter) was removed from scope by user decision on 2026-09-08 before it started; its id is retired and never reused.

## Discovered follow-ups

- [ ] `T47` Investigate crawl-run AI call/cost rollup showing 0 — agent, complexity: simple
  - Done when: the 2026-09-08 T44 refresh recorded 25 evaluations but `ai_call_count: 0` / `estimated_ai_cost: null` on the crawl run; find where evaluation-phase AI usage should be attributed to the crawl run (or document why it is only on evaluation records) and fix/report accordingly.
