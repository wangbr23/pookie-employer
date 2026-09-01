# Pookie Employer Implementation Design

**Date:** 2026-08-31
**Spec:** `docs/specs/pookie-employer.md`
**Mock:** `docs/specs/mocks/mock.png`

## Problem

Pookie Employer needs to turn a sensitive personal job-search profile into trustworthy job recommendations from external sources when she asks for a refresh. The core technical problem is not merely displaying jobs; it is building a small, reliable ingestion and ranking pipeline that can:

- collect jobs from public/ATS/company sources without hostile scraping;
- preserve source coverage/debug information so missed-source risk is visible;
- normalize and deduplicate postings;
- rank jobs against a profile with explainable fit buckets;
- present fresh results in a warm, simple dashboard with save/dismiss/apply actions.

## Requirements grounding

From `docs/specs/pookie-employer.md`, the MVP must include:

- automated external job discovery from day one;
- on-demand refresh for the first milestone, with daily scheduled refresh deferred until the product proves useful;
- first milestone support for a hardcoded/admin-configured profile before full onboarding;
- structured ATS platforms plus a small curated company/source list as the initial source set;
- legal/ToS-safe ingestion: avoid auth-gated, explicitly prohibited, anti-bot-bypass, and hostile scraping;
- coverage/debug visibility: last crawl time, sources searched, jobs found, source/platform/company coverage, failures, and pending source suggestions;
- qualitative fit buckets: Strong Fit, Possible Fit, Stretch, Needs Review;
- explanations of why a job fits, concerns/gaps, and what to verify;
- dashboard actions: view/filter/search, save, dismiss with reasons, and open apply link;
- duplicate merging while preserving all source/apply links;
- job states: New, Seen, Saved, Dismissed, Possibly closed, Closed/archived;
- sensitive-data handling, real auth if hosted, storage minimization, deletion/export controls;
- target ongoing MVP cost under $25/month.

Non-goals from the spec:

- no auto-applying;
- no resume/cover-letter generation;
- no application tracking pipeline or Applied state;
- no interview prep, outreach, negotiation tooling, browser extension, mobile app, multi-user SaaS/billing, or LinkedIn/Indeed auth scraping.

## Current-state grounding

This is a scaffolded project with no application code yet.

- `AGENTS.md` records the project description, leaves stack/commands as TBD, and requires small reviewable tasks.
- `CLEANCODE.md` requires simple direct solutions, small diffs, explicit domain states, input validation at boundaries, and careful handling of ambiguity/security/privacy.
- `docs/decisions.md` already records two load-bearing decisions: automated external job discovery is core MVP scope, and profile/job-search data must be treated as sensitive.
- `docs/specs/pookie-employer.md` is the product source of truth.
- `docs/specs/mocks/mock.png` provides visual direction for a warm, soft dashboard style; its sample non-software jobs are illustrative only.
- There is no current code, database schema, deployment, or package manager to preserve.

## Goals / Non-goals

### Goals

- Choose a minimal full-stack architecture that can ship the first milestone quickly.
- Define the data model and ingestion/ranking boundaries before implementation begins.
- Keep source ingestion observable and recoverable rather than a silent batch script.
- Keep AI calls behind explicit service boundaries so provider choice can change later.
- Preserve sensitive data constraints without overbuilding enterprise security.
- Split the design into small implementation slices suitable for `plan-tasks` and agent dispatch.

### Non-goals

- Implementing code in this document.
- Designing a general-purpose crawler platform.
- Building polished admin UI before config/scripts prove the workflow.
- Supporting multiple unrelated users, teams, billing, or public SaaS operations.
- Building resume generation, cover-letter generation, application tracking, or auto-apply.

## Design

### Stack pick

Use a **Next.js TypeScript frontend plus a dedicated FastAPI Python backend/worker**, backed by PostgreSQL, for the MVP.

Recommended concrete stack:

- Frontend runtime/language: TypeScript on Node.js.
- Frontend framework: Next.js App Router.
- Styling: Tailwind CSS, matching the soft visual direction in `docs/specs/mocks/mock.png`.
- Backend runtime/language: Python 3.12+.
- Backend framework: FastAPI.
- Backend jobs: FastAPI service functions plus on-demand API/CLI entrypoints for crawl/rank jobs; add scheduled refresh or a queue only when measured usage requires it.
- Database: PostgreSQL.
- Database access: SQLAlchemy 2.x + Alembic migrations on the backend. The frontend should access data through backend APIs, not direct database writes.
- Auth: simple hosted auth or provider-backed auth for the frontend, with backend API authorization and a single allowed account for MVP.
- AI provider adapter: one internal Python `ai` service interface, initially backed by a low-cost hosted LLM API chosen at implementation time.
- Scheduling: no daily cron in the first milestone. The dashboard triggers on-demand refresh through the backend; scheduled refresh is a later enhancement.

Why this pick:

- The MVP's core value is ingestion, normalization, deduplication, and AI ranking. Those are long-running backend concerns, not frontend concerns.
- Python/FastAPI gives broader access to AI, scraping, parsing, NLP, queueing, and data-processing libraries.
- Next.js remains a strong fit for the warm dashboard and fast UI iteration.
- PostgreSQL handles relational job/source/run data well and avoids premature search infrastructure.
- Keeping the frontend out of direct database writes gives a clearer privacy and authorization boundary.
- Starting with on-demand FastAPI API/CLI jobs is cheaper and simpler than introducing a scheduler or queue immediately, while preserving an obvious path to scheduled or queued workers later.

Update `AGENTS.md` after this design is accepted to record the selected stack and commands.

### Architecture overview

The application has two deployable services and five logical layers:

1. **Dashboard/UI layer — Next.js frontend**
   - Next.js pages/components for For You, Saved, All Jobs, Dismissed/Archived, Possibly Closed, and a simple debug/admin view.
   - Reads precomputed job recommendations from backend APIs; does not run expensive AI work during page load.
   - Sends user actions such as save, dismiss, mark seen, export, and on-demand refresh to the backend.

2. **Backend API layer — FastAPI**
   - REST endpoints for job lists, job detail, save, dismiss, mark seen, trigger crawl, rerun ranking, export saved jobs, and delete profile/history.
   - Validates all inputs using Pydantic schemas before database writes.
   - Owns authorization checks for sensitive/admin/destructive actions.

3. **Ingestion layer — FastAPI backend/worker code**
   - Source adapters for Greenhouse, Lever, Ashby, and curated company/public career URLs.
   - Produces normalized `RawJobPosting` records plus `CrawlRun`/`SourceRun` observability data.
   - Avoids auth-gated or hostile scraping; adapters must be allowlisted by source config.

4. **Normalization/deduplication/ranking layer — FastAPI backend/worker code**
   - Converts raw postings into canonical `Job` records.
   - Merges likely duplicates into one visible job while preserving multiple apply/source links.
   - Applies hard filters, AI extraction, fit bucket assignment, summary/concerns, and uncertainty flags.

5. **AI service layer — Python backend module**
   - Provides typed functions for job field extraction, fit evaluation, summary/concerns, and source suggestions.
   - Does not generate application materials.
   - Logs AI request metadata/cost estimate where possible, but not full sensitive prompts unless explicitly needed for debugging.

### Cross-service boundaries

The frontend/backend split is justified because ingestion, crawling, parsing, ranking, and AI evaluation are the MVP's product engine and benefit from Python's ecosystem. To avoid turning this into unnecessary microservice complexity, keep the boundary strict and boring:

| Concern | Owner | Notes |
| --- | --- | --- |
| Dashboard pages, layout, client interactions | Next.js frontend | No direct database writes. No crawler/ranker logic. |
| User session/login UI | Next.js frontend | May use a hosted auth provider or Auth.js-compatible flow. |
| API authorization decisions | FastAPI backend | Backend must enforce access even if frontend hides UI. |
| Job/source/profile/feedback database writes | FastAPI backend | Backend is the only service that writes domain data. |
| Database schema/migrations | FastAPI backend | SQLAlchemy/Alembic is the source of truth. Frontend consumes API contracts. |
| Crawl/rank execution | FastAPI backend | Triggered by authenticated backend endpoint or CLI for MVP; scheduler is deferred. |
| AI provider integration | FastAPI backend | Consent, prompt construction, output parsing, cost metadata, and redaction live here. |
| Static UI styling/mock implementation | Next.js frontend | Tailwind components should follow the mock's tone. |

Frontend-to-backend communication should use documented REST endpoints. FastAPI's generated OpenAPI schema is the contract source; generate or hand-maintain a small TypeScript API client/types from that schema once endpoint shapes stabilize. Do not duplicate business rules in TypeScript beyond presentation-friendly enum labels and form validation.

For MVP authentication, use one of these simple patterns during implementation:

1. **Shared auth provider/JWT:** frontend obtains a session token, backend verifies it and restricts access to one allowed user/email; or
2. **Frontend proxy with backend API secret:** frontend server routes call the backend using a server-only API key, while the frontend still authenticates the user before proxying.

Prefer the shared JWT approach if the chosen auth provider makes backend verification straightforward. Use the proxy/API-secret approach only if it significantly reduces setup for the personal MVP. In both cases, backend refresh/admin/destructive endpoints require explicit protection and must not rely on obscurity.

Operational conventions across services:

- Use consistent request IDs in frontend server calls and backend logs so crawl/action failures can be traced.
- Return structured backend errors with safe public messages; log sensitive details only on the backend and redact profile/prompt data.
- Keep CORS narrow: only the deployed frontend origin and local dev origin may call the backend.
- Backend owns database transactions; frontend treats backend responses as authoritative.
- Breaking API changes should be landed with matching frontend changes in the same reviewable task unless hidden behind backward-compatible fields.

### First milestone build shape

The first milestone should not wait for polished onboarding. It should include:

- a seeded/admin-configured single profile in the database or config seed;
- a seeded source list covering a few companies across Greenhouse, Lever, and Ashby where allowed;
- scripts or protected on-demand endpoints to run crawl and ranking;
- a simple dashboard styled after the mock;
- a debug view for crawl/source coverage.

Full resume upload and profile editing come after the pipeline proves useful.

### Ingestion approach

Represent every crawl as a `CrawlRun`, with per-source `SourceRun` rows. A source run records status, started/finished time, jobs discovered, jobs inserted/updated, jobs skipped, and an error summary if any.

Initial adapters:

- **Greenhouse adapter:** consume public Greenhouse job board endpoints/pages for allowlisted companies.
- **Lever adapter:** consume public Lever postings for allowlisted companies.
- **Ashby adapter:** consume public Ashby postings for allowlisted companies.
- **Generic company source adapter:** fetch and parse low-friction public career URLs only when explicitly allowlisted. Keep this adapter conservative; if parsing is unreliable, create raw records marked Needs Review rather than expanding scraper complexity.

Do not implement broad web crawling in the first milestone. Search-engine/source discovery should be a later feature that proposes new sources for approval, not an automatic crawler.

### Deduplication approach

Use conservative deterministic deduplication first:

- canonical company name;
- normalized title;
- normalized location/remote policy;
- source posting ID when available;
- apply URL/domain when available.

If two postings match strongly, merge them into one `Job` and preserve all `JobLink` rows. If uncertain, do not merge; duplicate clutter is less harmful than hiding a legitimate different role.

### Ranking approach

Ranking is a stored result, not computed live on dashboard load. A `JobEvaluation` stores:

- fit bucket;
- ranking score for internal sorting only;
- matched skills/preferences;
- concerns/gaps;
- uncertainty flags;
- model/provider/version metadata;
- evaluated timestamp.

The visible UI should show buckets and explanations, not numeric scores.

Use a two-step ranking path:

1. Deterministic prefiltering and metadata checks for hard constraints and obvious rejects.
2. AI-assisted evaluation for jobs that pass or are uncertain enough to review.

Jobs with missing salary or unclear remote/work-auth details should usually remain visible, ranked lower or placed in Needs Review, unless they contradict explicit hard filters.

### Dashboard approach

Build these views:

- **For You:** default view, new jobs since last visit grouped by fit bucket.
- **Saved:** saved jobs count and list.
- **All Jobs:** active non-dismissed jobs, filterable/searchable.
- **Dismissed/Archived:** dismissed and closed jobs.
- **Debug/Coverage:** internal view for last crawl, source statuses, counts, and errors.

Each job card should include:

- company initials/logo placeholder;
- company name and title;
- badges for location/remote, employment type if available, salary if available/unknown;
- fit bucket or Needs Review label;
- save button;
- dismiss button with reason flow;
- Apply link opening the canonical or best available apply URL;
- expandable details with fit explanation, concerns, source links, and raw posting timestamp.

The mock should guide color, spacing, rounded cards, and soft tone, but software-engineering job metadata and fit explanations take priority over exact visual fidelity.

### Privacy and access approach

For any hosted deployment:

- require authentication;
- restrict access to a single configured user/email for MVP;
- protect backend refresh/admin endpoints with auth and, where needed, a server-only API secret;
- use a database/hosting provider with encryption at rest;
- avoid storing raw resume files in milestone one because the profile is admin-configured;
- when onboarding is added, extract structured profile data and delete the raw upload unless the user explicitly chooses retention;
- if raw resumes or highly sensitive optional fields are retained later, encrypt those values at the application level before storage;
- provide MVP actions to delete profile-derived data, delete job feedback/history, and export saved jobs.

Before enabling third-party AI calls, add an explicit consent setting for the user/profile and record the provider/model family allowed for matching. Review provider data-retention terms during implementation; prefer providers/settings that do not train on submitted data. Do not require an enterprise DPA or on-prem model for the personal MVP unless provider terms make ordinary API use unacceptable.

Do not store full AI prompts/responses containing sensitive profile data by default. Store structured outputs and minimal model metadata. If debug logging is needed, add redaction or short retention.

### Cost approach

Control cost by:

- running AI ranking only on new or materially changed jobs;
- caching `JobEvaluation` by job content hash + profile version;
- batching or rate-limiting AI calls;
- starting with curated source lists rather than broad crawling;
- making on-demand refresh explicit and statusful;
- storing per-run AI call counts and estimated cost;
- adding a configurable monthly AI budget/soft cap and surfacing a warning when usage approaches it.

### On-demand refresh performance approach

The first milestone uses **on-demand refresh only**. It should feel interactive and target a **90-second refresh budget** for the approved source set. The goal is not to guarantee every source always finishes; the goal is to return useful, fresh results quickly and record what did not finish.

Backend refresh policy:

- Fetch approved sources concurrently with bounded concurrency.
- Apply strict per-source timeouts, initially around 8 seconds.
- Apply a total crawl budget, initially around 60 seconds.
- Reserve the remaining budget, initially around 30 seconds, for normalization/dedupe and AI evaluation.
- Skip unchanged postings using `contentHash` and profile version where applicable.
- Run deterministic filtering before AI evaluation.
- Cap AI evaluations per refresh, initially around 25 new/changed jobs.
- If more jobs need evaluation, mark the remaining work as pending and let the user run another ranking pass later.
- Record partial results, skipped unchanged jobs, slow/failed sources, pending evaluations, elapsed time, and AI cost metadata.

Dashboard refresh UX:

- Show a `Refresh jobs` action rather than implying automatic daily updates.
- Show status while refresh runs: sources searched, jobs found, jobs evaluated, slow/failed sources, and pending evaluations.
- Display partial results as soon as the backend run completes within budget.
- Do not make the user wait for slow sources or all AI evaluations before showing useful results.

Daily scheduled refresh is a later enhancement. Add it only if she wants proactive updates after on-demand refresh proves useful.

### Failure handling

Partial crawl success is expected. A failed source should not fail the whole run. Store source-level errors, retry failed sources later, and only surface repeated failures prominently.

Track crawl duration and source counts in `CrawlRun`/`SourceRun`. If on-demand refresh routinely exceeds the 90-second budget, needs background continuation, or regularly requires concurrent execution, migrate the crawl/evaluation pipeline from synchronous FastAPI API/CLI jobs to a queue-backed worker. Do not introduce the queue before the simple backend job approach proves insufficient.

If an apply link fails:

- mark the associated job possibly closed;
- try alternate preserved links;
- attempt a conservative re-check of the company/source page;
- show a dashboard warning instead of immediately deleting the job.

## Data / interfaces

### Core database tables

Names are conceptual; exact SQLAlchemy model names can match these.

#### UserProfile

Single-user for MVP but shaped to avoid blocking future multi-user support.

- `id`
- `ownerUserId`
- `targetRoleFamilies: string[]`
- `seniorityMin`, `seniorityMax`
- `remotePreference`
- `allowedLocations: string[]`
- `workAuthorizationConstraints: string[]`
- `salaryFloor`
- `preferredTech: string[]`
- `avoidedTech: string[]`
- `preferredIndustries: string[]`
- `avoidedIndustries: string[]`
- `companyStagePreferences: string[]`
- `dealbreakers: string[]`
- `notes`
- `profileVersion`
- timestamps

#### JobSource

- `id`
- `kind`: `greenhouse | lever | ashby | company_page`
- `name`
- `companyName`
- `baseUrl`
- `externalBoardId`
- `status`: `active | paused | needs_review`
- `approvalStatus`: `approved | suggested | rejected`
- `lastSuccessfulCrawlAt`
- `lastErrorAt`
- `lastErrorSummary`
- timestamps

#### CrawlRun

- `id`
- `trigger`: `on_demand | manual_script | scheduled`
- `status`: `running | partial_success | success | failed`
- `startedAt`, `finishedAt`
- aggregate counts: sources attempted/succeeded/failed, jobs discovered/new/updated/skipped, evaluations completed/pending
- timing/cost fields: elapsed milliseconds, AI call count, estimated AI cost

#### SourceRun

- `id`
- `crawlRunId`
- `jobSourceId`
- `status`: `running | success | failed | skipped`
- `startedAt`, `finishedAt`
- counts: discovered/inserted/updated/skipped
- `errorSummary`

#### RawJobPosting

- `id`
- `jobSourceId`
- `sourcePostingId`
- `sourceUrl`
- `applyUrl`
- `rawTitle`
- `rawCompany`
- `rawLocation`
- `rawDescription`
- `contentHash`
- `firstSeenAt`
- `lastSeenAt`
- `closedDetectedAt`

#### Job

- `id`
- `canonicalTitle`
- `canonicalCompany`
- `canonicalLocation`
- `remotePolicy`: `remote | hybrid | onsite | unclear`
- `employmentType`
- `salaryMin`, `salaryMax`, `salaryCurrency`, `salaryUnknown`
- `seniority`
- `status`: `new | seen | saved | dismissed | possibly_closed | closed_archived`
- `fitBucket`: `strong | possible | stretch | needs_review`
- `createdAt`, `updatedAt`, `firstSeenAt`, `lastSeenAt`

#### JobLink

- `id`
- `jobId`
- `rawJobPostingId`
- `sourceUrl`
- `applyUrl`
- `isPrimary`
- `lastCheckedAt`
- `status`: `active | broken | possibly_closed | closed`

#### JobEvaluation

- `id`
- `jobId`
- `profileId`
- `profileVersion`
- `jobContentHash`
- `fitBucket`
- `internalScore`
- `matchedSkills: string[]`
- `matchedPreferences: string[]`
- `concerns: string[]`
- `uncertainties: string[]`
- `summary`
- `verifyBeforeApplying: string[]`
- `salaryUncertainty`: `known | unknown | estimated | conflicting`
- `remoteUncertainty`: `clear | unclear | conflicting`
- `workAuthUncertainty`: `clear | unclear | conflicting`
- `modelProvider`
- `modelName`
- `evaluatedAt`

#### JobFeedback

- `id`
- `jobId`
- `profileId`
- `action`: `save | dismiss | more_like_this | less_like_this | ai_wrong`
- `reasons: string[]`
- `freeText`
- `createdAt`

### Internal service interfaces

Keep these as small modules/functions, not classes unless needed.

- `crawlSources(trigger): Promise<CrawlRunSummary>`
- `crawlSource(source): Promise<RawJobPosting[]>`
- `normalizePosting(raw): Promise<NormalizedJobCandidate>`
- `dedupeAndUpsert(candidate): Promise<Job>`
- `evaluateJob(job, profile): Promise<JobEvaluation>`
- `rerankUnevaluatedJobs(profile): Promise<void>`
- `saveJob(jobId, reasons)`
- `dismissJob(jobId, reasons, freeText?)`
- `exportSavedJobs(profileId): Promise<CsvOrJson>`
- `deleteProfileData(profileId)`

### API/routes

The Next.js frontend owns UI routes; the FastAPI backend owns data/action APIs.

Frontend routes:

- `GET /` or `/for-you` — default dashboard.
- `GET /saved`
- `GET /jobs`
- `GET /archived`
- `GET /debug/coverage`

Backend API endpoints:

- `GET /api/jobs` — list/filter jobs for dashboard views.
- `GET /api/jobs/{id}` — job detail with evaluation and links.
- `POST /api/jobs/{id}/save`
- `POST /api/jobs/{id}/dismiss`
- `POST /api/jobs/{id}/seen`
- `POST /api/crawl/run` — authenticated on-demand trigger.
- `GET /api/crawl/runs/{id}` — authenticated refresh status/result endpoint.
- `POST /api/rank/run` — admin/protected reranking.
- `GET /api/debug/coverage`
- `GET /api/export/saved`
- `DELETE /api/profile`
- `DELETE /api/job-history`

## Deployment plan

Keep the monorepo. The production deployment should point each platform at the relevant subdirectory rather than splitting repositories.

Recommended first deployment path:

- **Frontend:** Vercel project with root directory `frontend/`.
- **Backend:** Railway or Render web service with root directory `backend/`.
- **Database:** managed PostgreSQL, preferably on the same provider as the backend for the first MVP unless Neon/Supabase is clearly easier.
- **Durability:** production uses managed PostgreSQL with persistent storage/backups. The Docker Compose PostgreSQL service and `localhost` `DATABASE_URL` are local-development only.
- **Refresh:** no production scheduler for the first milestone. The dashboard calls the backend on-demand refresh endpoint. Scheduled refresh can be added later if desired.

For a one-user MVP, optimize for low cost and low operational overhead:

- Prefer free/trial tiers during development if they support the needed runtime and durable database constraints.
- Do not depend on an ephemeral/free database for real use; if the free database can expire or be wiped, treat it as development-only.
- Use environment variables for production secrets: `DATABASE_URL`, auth settings, backend API auth/proxy secret if used, allowed frontend origins, and AI provider keys once approved.
- Restrict backend CORS to the deployed Vercel origin plus local dev origins.
- Keep backend admin/refresh endpoints protected even though there is only one user.

Railway is likely the simplest early single-provider path because it can host FastAPI and managed Postgres together. Vercel remains a good fit for the frontend. Render is also acceptable for the FastAPI backend and managed Postgres if its pricing/sleep behavior is acceptable.

## Risks

### Source coverage may disappoint before search expansion

Curated ATS/company sources can prove the pipeline but may not find enough roles. Mitigation: make coverage visible from milestone one and treat source expansion as a near-term follow-up.

### Scraping/ToS ambiguity

Even public pages can have unclear terms or brittle markup. Mitigation: start with structured public ATS endpoints/pages and explicit allowlists; avoid auth-gated or hostile sources.

### AI ranking quality may be noisy

The first evaluator may over/under-rank jobs or misread unclear requirements. Mitigation: show concerns/uncertainties, collect dismiss/save reasons, allow Needs Review, and cache evaluations by profile/content versions for debugging.

### Sensitive data exposure through logs or AI prompts

Resume-derived profile information may leak through application logs or provider calls. Mitigation: do not log full prompts/responses by default; store structured outputs; require explicit consent for third-party AI; keep profile fields minimal.

### Cross-service auth or API drift may create security and maintenance bugs

A split frontend/backend architecture adds another boundary where auth assumptions, CORS, API schemas, and error handling can drift. Mitigation: backend enforces authorization for every sensitive action, FastAPI OpenAPI is the API contract source, CORS is allowlisted, and breaking API changes land with matching frontend changes.

### On-demand refresh may exceed the 90-second UX budget

A protected FastAPI endpoint or CLI job is simple, but slow sources or too many AI evaluations can make the user wait too long. Mitigation: use bounded source concurrency, strict per-source and total timeouts, unchanged-job skipping, AI evaluation caps, partial results, and explicit pending-evaluation reporting. Move to a queue-backed worker only when measured refresh times prove the synchronous backend job is insufficient.

### Dashboard can become cluttered

Fit buckets and job states help, but dedupe uncertainty and Needs Review jobs can accumulate. Mitigation: filter/search, old job access, explicit archived/dismissed views, conservative defaults.

## Rollout

1. **Project foundation**
   - Initialize a Next.js/TypeScript/Tailwind frontend and a FastAPI/Python backend.
   - Add backend env validation, frontend env validation, auth skeleton, and base layout styled after the mock.

2. **Schema and seed data**
   - Add SQLAlchemy models and Alembic migrations for profile, sources, crawl runs, raw postings, jobs, links, evaluations, and feedback.
   - Seed one profile and a small approved source list.

3. **Source adapters and crawl observability**
   - Implement Greenhouse, Lever, Ashby adapters and conservative company-page adapter.
   - Record crawl/source runs and raw postings.

4. **Normalize, dedupe, and status model**
   - Normalize postings, upsert canonical jobs, preserve links, and implement job lifecycle states.

5. **AI evaluation service**
   - Add typed AI adapter and job evaluation pipeline.
   - Store fit buckets, summaries, concerns, uncertainty, and metadata.

6. **Dashboard MVP**
   - Implement For You, Saved, All Jobs, Archived/Possibly Closed, job cards, filters, apply links, save/dismiss feedback.

7. **On-demand refresh triggers and debug view**
   - Add protected backend on-demand refresh endpoint, CLI entrypoint, reranking trigger, refresh status endpoint, and coverage/debug page. Daily scheduled refresh stays deferred.

8. **Privacy/data controls**
   - Add export saved jobs, delete profile-derived data, delete feedback/history.

9. **Onboarding follow-up**
   - Add resume upload, extraction, confirmation/edit flow, and profile versioning after the first pipeline milestone is validated.

## Verification

### Automated checks

- Typecheck/lint/build pass once commands are established in `AGENTS.md`.
- Unit tests for:
  - source adapter parsing using fixture responses;
  - normalization and minimum-field validation;
  - deterministic deduplication cases;
  - job state transitions;
  - hard-filter behavior for location/work-auth/salary/seniority;
  - feedback reason persistence;
  - API authorization on crawl/admin/destructive endpoints.

### Integration checks

- Frontend can fetch dashboard jobs from FastAPI using the chosen auth pattern; unauthenticated requests are rejected.
- Backend CORS allows only local/dev and deployed frontend origins.
- FastAPI OpenAPI schema covers job list/detail, feedback, on-demand refresh trigger/status, debug coverage, export, and deletion endpoints.
- Seed profile + source list can run a crawl and create `CrawlRun`, `SourceRun`, `RawJobPosting`, `Job`, and `JobLink` records.
- Re-running the same crawl updates `lastSeenAt` and does not create duplicate visible jobs.
- AI evaluation creates stored `JobEvaluation` rows and dashboard reads cached evaluations without live AI calls.
- Partial source failure produces partial results and records the failed `SourceRun`.
- Repeated source failures are visible in the debug view without blocking successful sources.
- Broken apply-link check marks a link/job possibly closed without deleting it.
- Refresh duration, source counts, AI call count, estimated AI cost, slow/failed sources, and pending evaluation count are recorded per run.
- On-demand refresh with fixture/seeded sources respects the configured per-source timeout, total crawl budget, AI evaluation cap, and target 90-second UX budget.

### Product acceptance checks

- Dashboard default shows new jobs grouped by Strong Fit/Possible Fit/Stretch/Needs Review.
- Saved count and Saved page update after saving a job.
- Dismiss flow records structured reason and removes the job from For You/All active views.
- Apply button opens a preserved apply link.
- Dashboard provides a Refresh jobs action and shows refresh status/result instead of depending on daily scheduled refresh.
- Debug view shows last refresh time, sources searched, jobs discovered/new, source errors, elapsed time, and pending evaluations.
- Old jobs remain accessible outside the default new-jobs view.
- Sensitive/destructive actions require authentication.

### Manual MVP usefulness check

After real sources are seeded, run the system for several days and verify qualitatively that it saves time, finds relevant software engineering roles worth saving/applying to, and exposes enough source coverage information to guide expansion.

Track lightweight quantitative signals during this check:

- saved jobs per week;
- dismissed jobs by reason;
- percentage of shown jobs marked save-worthy;
- number of discovered jobs she believes she would not have found manually;
- obvious duplicate rate in the dashboard;
- number of source failures and stale/broken apply links.

These metrics are guide rails, not hard product success gates; the personal MVP still succeeds or fails on whether she actually finds the recommendations useful.
