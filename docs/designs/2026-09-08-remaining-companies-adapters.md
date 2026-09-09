# Remaining companies: source adapter research (T45)

Date: 2026-09-08
Status: Decided — direct per-company/ATS adapters (option A). Paid aggregator rejected.

## Context

T38's company list left 16 target companies without a source: Google, Amazon, Microsoft,
Apple, Adobe, Uber, Databricks, MongoDB, Atlassian, Oracle, Bloomberg, Spotify, Tesla,
Snap, X (Twitter), Shopify. T45 asked for an aggregator adapter (e.g. SerpApi Google Jobs).
This research probed each company's careers site/API on 2026-09-08 and compared approaches.

## Probing findings

### Verified via existing adapters (seed only, zero new code)

| Company | Backend | Evidence |
|---|---|---|
| Databricks | Greenhouse | `boards-api.greenhouse.io/v1/boards/databricks/jobs` returns full JSON |
| MongoDB | Greenhouse | `boards-api.greenhouse.io/v1/boards/mongodb/jobs` returns full JSON |

### Verified reachable, needs its own adapter

| Company | Backend | Evidence |
|---|---|---|
| Amazon | Own site, public JSON API `amazon.jobs/en/search.json` | 103KB live job JSON returned to a plain fetch |
| Apple | Own site; server-rendered listings **with full descriptions**; known JSON API (`POST jobs.apple.com/api/role/search`) used by public scrapers | Search page rendered 600+ roles in plain HTML |
| Adobe | **Phenom People** — server-rendered search pages, parsed by the Phenom adapter (T46) | `careers.adobe.com/us/en/search-results?from=N` embeds 10 jobs/page in `phApp.ddo` JSON with descriptions (see T46 findings below) |

### Blocked from this session's probes — verify from a dev machine (browser or curl)

Plain webfetch was bot-blocked or JS-walled for these; careers sites almost always expose
a JSON listing API that the browser's network tab reveals:

- **Microsoft** — known unofficial JSON API `gcsservices.careers.microsoft.com/search/api/v1/Search` (transport error here; widely used, verify)
- **Tesla** — `jobs.tesla.com` bot-blocked; known JSON API pattern, verify via browser
- **Spotify** — custom site (lifeatspotify.com); SmartRecruiters ids `spotify`/`Spotify` returned 0 results; `/api/jobs` 404 — inspect network tab
- **X (Twitter)** — careers.x.com returns 403 to plain fetches
- **Bloomberg** — careers.bloomberg.com returns 403 to plain fetches
- **Uber** — JS app; find listing API via network tab
- **Snap** — candidate paths 404; inspect network tab
- **Atlassian** — not on Greenhouse (404); JS shell page; inspect network tab
- **Oracle** — JS app (Oracle Recruiting Cloud); REST exists but complex/auth-y
- **Shopify** — careers page is server-rendered with jobs inline (verified), but no obvious JSON API; HTML parsing is the fallback

### No API at all

- **Google** — no public careers API. Under option A (no paid aggregator, no scraping),
  Google cannot be covered. Deferred unless the user later approves scraping or an aggregator.

## Approaches considered

### A. Per-ATS/company direct adapters (chosen)
Pros: best data quality (exact postings, stable apply URLs, official source, clean dedupe),
no recurring cost, descriptions often included (fixes the Workday/Netflix "Needs Review"
problem), matches existing adapter pattern. Cons: N adapters to build/maintain, hardest
companies (Google) uncovered, some sites bot-block. Complexity: low per adapter (Netflix
took ~a day); each is one reviewable task (T41–T44 precedent).

### B. SerpApi Google Jobs aggregator (rejected)
Pros: one integration covers all 16 incl. Google; rich payloads (description, qualifications,
posted date, salary, multiple apply links); SerpApi absorbs scraping/bot-block burden;
~160 searches/refresh fits the $75/mo 5k-search plan. Cons: recurring cost (user rejected);
search-based so completeness not guaranteed (missing/stale jobs); apply links often route
through Google/LinkedIn rather than the canonical company URL (weaker dedupe identity and
apply-link preservation); company filtering is on us. Complexity: one complex adapter plus
fuzzier dedupe rules.

### C. Free aggregators — Adzuna, The Muse, Jooble (rejected)
Free tiers, but coverage of these specific companies is spotty and stale; would still end
up building A. Not worth a spike.

### D. Headless-browser scraping (rejected)
Covers anything, but brittle, ops-heavy, slow (endangers the 90s refresh budget), and a
bot-block arms race. Out of MVP scope.

## Decision

Hybrid option A, in value order (tasks in TODO.md):

1. **T45** Seed Databricks + MongoDB via the existing Greenhouse adapter (free, immediate).
2. **T46** Implement a Phenom adapter (done 2026-09-09 — see findings below) — **T48** seeds Adobe.
3. **T51** Apple (`role/search`) adapter — verified reachable; **T52** seeds it. Serialized
   behind T46 because each adapter adds a `SourceKind` enum value + migration +
   `refresh.py` dispatch branch + frontend union (same files). Amazon was dropped from
   the target list by user decision on 2026-09-08 (its planned adapter, T50, was retired
   before starting; the `search.json` finding above stays on record in case it returns).
4. **T49** Verify the bot-blocked/unknown backends from a dev machine (browser network tab
   or curl), record results here, then create adapter tasks for whatever is directly
   API-able. Google and anything scraper-hostile (X, Bloomberg, Shopify's no-API site)
   stay uncovered unless the user reconsiders.

## Open items

- Spotify backend unknown (Phenom suspected but unverified) — seed after T49.
- Whether to revisit scraping/aggregator for Google, X, Bloomberg — user decision, deferred.

## T46 implementation findings (2026-09-09)

The original T46 premise — paginate Phenom's `/api/apply/v2/jobs` API — was wrong. That
path is Eightfold's API, not Phenom's: `careers.adobe.com/api/apply/v2/jobs` answers
`{"errorMsg":"Tenant not identified"}` for *every* `domain` value (`adobe.com`, `adobe`,
`careers.adobe.com`, `ADOBUS`, …). The "right endpoint, wrong param" note in the probing
table was a red herring; there is no per-tenant domain param on that endpoint at all.

How Phenom boards actually work (verified live against `careers.adobe.com`):

- Each `GET https://careers.adobe.com/us/en/search-results?from={offset}` page embeds its
  10 results in the page's `phApp.ddo = {...}` bootstrap JSON at
  `eagerLoadRefineSearch.data.jobs`, with `eagerLoadRefineSearch.totalHits` (650) for
  pagination planning and clean overflow (`from=1000` → 0 jobs).
- Entry fields: `jobSeqNo` (unique id), `reqId` (R-number), `title`, `applyUrl`,
  `location`/`multi_location`/`cityStateCountry`, `descriptionTeaser` (short blurb —
  present on all 650 postings), `experienceLevel`, `type`, `category`, `postedDate`.
- No auth, no CSRF, no cookies needed for the page fetch. (The `POST /widgets` search API
  needs a session + `x-csrf-token` and still answers `{"refineSearch":{"tokenAvailable":false}}`
  from a plain client — it is not usable and not needed; the server-rendered pages suffice.)
- Locale path prefix (`us/en`) varies per tenant, so `external_board_id` stores the
  search-results path (e.g. `us/en/search-results`) and `base_url` the careers host.

Live verification: 650 postings fetched in 7.4s (4-way page pool, same pattern as
Netflix/Workday), all ids unique, 100% with title/location/description, spot-checked
apply URLs return HTTP 200.

Note for T48/dedupe: Adobe's Phenom `applyUrl`s point at Adobe's own Workday tenant
(`adobe.wd5.myworkdayjobs.com/external_experienced`, 703 postings — reachable with the
existing Workday adapter). Seeding Adobe via *both* platforms would surface
near-duplicate cards and double AI calls, since T19 dedupe keeps uncertain duplicates
separate — pick one source for Adobe (user chose Phenom, for the descriptions).
