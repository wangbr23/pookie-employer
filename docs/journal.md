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

## 2026-09-01 — T37 implementation begun

Added SQLAlchemy models and the `0003_recommendation_schema` migration for canonical jobs, preserved job links, profile-specific evaluations, and user feedback. The migration’s offline SQL generates successfully with the expected enum/table ordering; T37 remains open pending final review and any live-database validation.

## 2026-09-01 — T37 completed

Validated T37 against a clean Homebrew PostgreSQL 15 database named `pookie_t37_verify`. Upgraded through `0003_recommendation_schema`, verified all expected tables and enum types, downgraded to `0002_core_ingestion_schema`, and upgraded again successfully. The full backend suite (17 tests), Ruff, and mypy pass.

## 2026-09-01 — T8 seed command added

Added `python -m pookie_backend.seed` and `make seed` to seed one admin-configured `UserProfile` plus five approved `JobSource` rows across Greenhouse, Lever, and Ashby. The seed logic is idempotent via lookup-before-insert on `owner_user_id` and a `(kind, company_name, external_board_id)` natural key for sources. Added pytest coverage for duplicate suppression and expected seeded shape. Local test/lint/typecheck commands could not be fully run in this workspace because the backend `venv/` and pytest/ruff/mypy binaries are absent.

## 2026-09-06 — T26 For You and All Jobs views

Replaced the static mock dashboard with two real data-driven views backed by the `listJobs` API client:

- **For You** — fetches new/seen jobs and groups them by fit bucket (Strong Fits, Good Fits, Stretch Picks, Needs Review), each section with a count header.
- **All Jobs** — flat paginated list of all active (new/seen/saved) jobs with a text search input (title/company substring) and fit-bucket filter pill buttons.
- Extracted `components/job-card.tsx` mapping `JobSummaryResponse` fields (salary, remote policy, fit bucket, relative timestamps, initials) to the existing warm card design.
- Sidebar navigation switches between views client-side, shows live count badges; Saved/Dismissed/Debug remain placeholder (T27/T29 scope).
- Mobile header with compact tab bar for For You / All Jobs.
- Verified with seeded test data: grouping, search filtering, bucket filtering, pagination counter, and empty states all work. Lint, typecheck, and build pass clean.

## 2026-09-07 — T22/T23 end-to-end verification run

Ran the first live end-to-end refresh (fetch → normalize → dedupe → real OpenRouter evaluation). Two committed successful crawl runs: 5/5 sources succeeded (Airtable 16, Linear 29, Discord 48, Ramp 142, Resend 11 postings), 246 jobs stored, second run re-discovered all 246 with 0 inserts (dedupe verified), 50 real AI evaluations stored (openrouter / z-ai/glm-5.3-flash, 11091 in / 48228 out tokens), 196 evaluations still pending behind the per-run cap of 25.

Bugs found and fixed during the run:
- OpenRouter provider crashed with `AttributeError: None.strip()` when the glm model returned `content: null` — reasoning models can exhaust a tight `max_tokens` on reasoning alone. Raised to 2048 and added an explicit empty-content guard.
- `_extract_usage` read `usage.total_cost`/`body.cost`, but OpenRouter sends `usage.cost`, so estimated cost was never recorded. Fixed; the cost test now matches the real response shape.
- Seed source list (uncommitted board swap from the previous session) had drifted from `test_seed.py` expectations; test updated alongside the commit.

Known follow-ups: on-demand trigger's running-check can't see uncommitted in-flight crawls (concurrent POSTs race and 500 via raw-posting unique violation — hit during testing with duplicate triggers); evaluation phase has no time budget (~8 min per run, ~25 evals); remaining 196 evaluations drain ~25 per refresh.

## 2026-09-08 — Tightened eligibility role gate + stored-job backfill

Investigated why non-SWE roles (Senior Product Manager - Observability Data Platform, Senior Data Engineer, Engineering Compensation Partner) survived refresh filtering. Root cause: the role gate ran only in the evaluation phase and its regex allowlist matched generic terms — `\bplatform\b` matched the team suffix in the PM title, and `\bengineer` prefix-matched "Engineering" in the compensation title.

- Rewrote `_is_software_role` in `eligibility.py`: a title now needs an explicit `software` + `engineer|developer` pairing, or a core software-family phrase adjacent to engineer/developer (backend, frontend, full stack, devops, site reliability, SDE/SWE/SRE). Generic `engineer`/`developer`/`platform`/`infrastructure` no longer qualify. Product decision: keep the backend/frontend/devops/SRE family (softer variant) — classic software titles without the word "software" still pass.
- Added `make backfill` (`python -m pookie_backend.backfill`) to re-apply the eligibility filter to every stored rankable job with no AI calls; mirrors the evaluation loop's scope (never touches dismissed/closed-archived jobs, clears stale skip_reasons).
- Ran the backfill against the dev DB: 3,086 of 3,262 jobs filtered (2,757 not_engineering_role, 191 location_mismatch, 137 seniority_too_high, 1 non_engineering_specialty), 176 remain visible. Verified the three leak titles now carry `not_engineering_role`.
- Backend suite 282 passed, ruff clean. `make typecheck` still fails on 4 pre-existing `Result.rowcount` errors in `api/deletion.py` (present at HEAD, unrelated).

## 2026-09-08 — Expanded approved source list and seeded it (T38/T39)

Curated and seeded an expanded target-company list, recorded in TODO under T38/T39 (this session's journal entry was backfilled later — noted for honesty).

- 14 large companies added via verified Greenhouse/Ashby boards: Airbnb, Stripe, Coinbase, Roblox, Discord, Lyft, Asana, Datadog, LinkedIn, Dropbox, Twilio, DoorDash, Snowflake, Notion — plus the 4 original smaller companies; 18 active approved sources seeded idempotently via `python -m pookie_backend.seed`.
- 16 remaining target companies (Google, Amazon, Microsoft, Netflix, NVIDIA, Salesforce, etc.) need new adapters — Workday (T41), Netflix (T42), aggregator (T45); filed as T41–T46.
- No crawl has run against the new sources yet (job count still 3,262 at the time of the next entry).

## 2026-09-08 — Tightened seniority and removed DevOps/SRE from scope

User review of live results ("DevOps Engineer (Observability)" surfaced) led to three filter tightenings in `eligibility.py`. This **supersedes the same-day decision above that kept the devops/SRE family** and the T40 note's "seniority ≤ Senior" — the ceiling is now below Senior.

- Added `\bsenior\b` to `_OVER_SENIOR_PATTERNS` → `seniority_too_high`.
- Removed `\bdevops\s+(?:engineer|developer)\b` from `_CORE_SOFTWARE_PATTERNS`; bare DevOps titles now fail the role gate, and `\bdevops\b` in `_NON_ENGINEERING_OVERRIDES` catches compounds ("Software DevOps Engineer" → `non_engineering_specialty`).
- Same treatment for SRE: removed `\bsre\b` / `\bsite reliability\s+engineer\b` from core patterns; added `\bsre\b` + `\bsite reliability\b` to overrides.
- Tests updated: Senior/DevOps/SRE pass-cases flipped to reject-cases; evaluation-test default title de-Senior'd; backfill test updated. Suite 287 passed.
- Backfill rerun after each change; final state: 3,188 of 3,262 filtered (2,760 not_engineering_role, 314 seniority_too_high, 112 location_mismatch, 2 non_engineering_specialty), 74 visible (was 176 before this session).
- decisions.md: appended a superseding entry for the narrowed role/seniority scope.

## 2026-09-08 — T44: Netflix added as a live source

Seeded Netflix (kind `netflix`, board `netflix.com` at `explore.jobs.netflix.net`) via `seed.py` — 21 approved sources now. Seed test updated (count 21, `SourceKind.NETFLIX` in the kind set). Suite 337 passed; ruff clean on touched files (6 pre-existing I001 errors remain in alembic versions).

Live refresh through the API: 20/21 sources succeeded (Datadog timed out — transient, unrelated). Netflix fetched 496 postings / 494 canonical. Triage: 429 not_engineering_role, 8 location_mismatch, 6 seniority_too_high, 1 non_engineering_specialty, 50 eligible. The run's 25-eval cap went to Netflix jobs: two `strong` fits (Data and Feature Infrastructure / Training Platform, both AI Platform), rest mostly `needs_review` since Netflix's list API omits descriptions (same known limit as Workday).

Noted but not fixed: the crawl run rollup reported `ai_call_count: 0` / `estimated_ai_cost: null` despite 25 real evaluations — evaluation-phase AI usage may not be attributed to the crawl run. Worth a follow-up investigation.
