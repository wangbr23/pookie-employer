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

### Blocked from earlier probes — verified from a dev machine 2026-09-09 (T49)

All ten companies were re-probed from a dev machine (Chrome network tab + curl/httpx).
Results below; full detail in the T49 findings section at the bottom of this doc.

- **Microsoft** — verified: new JSON API, plain curl OK, descriptions available
- **Tesla** — listing API exists but Akamai bot-blocks all plain clients (403/429 challenge)
- **Spotify** — verified: own WordPress REST API (not Phenom), plain curl OK
- **X (Twitter)** — verified: careers.x.com → x.ai posts to a public Greenhouse board `xai`
- **Bloomberg** — verified: Avature site, server-rendered HTML with offset pagination, plain curl OK
- **Uber** — verified: JSON API behind Cloudflare; httpx passes (curl's TLS fingerprint is challenged)
- **Snap** — verified: Workday tenant (`snapchat/snap`) answers the existing Workday adapter
- **Atlassian** — verified: one JSON endpoint with all 243 jobs + descriptions, plain curl OK
- **Oracle** — verified: Oracle Recruiting Cloud REST API, plain curl OK, offset pagination
- **Shopify** — no JSON API (Ashby board is private); jobs embedded in the `/careers` page's
  streamed JSON payload, parseable with plain curl

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

- ~~Spotify backend unknown~~ — resolved by T49: own WordPress REST API (see findings).
- Whether to revisit scraping/aggregator for Google, Tesla (Akamai-blocked), Shopify
  (embedded-stream parse) — user decision, deferred.

## T49 verification findings (2026-09-09)

Probed from a dev machine with a real Chrome (Playwright) and curl/httpx. Verdicts drive
the new adapter tasks T53–T59 in TODO.md.

| Company | Backend | Verdict | Listing API (verified working) | Count | Descriptions |
|---|---|---|---|---|---|
| Microsoft | Own site, PCSx JSON API (Eightfold-powered) | Own adapter | `GET apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&start={offset}&pgSz=10` | 2253 | Yes, via `GET .../api/pcsx/position_details?position_id={id}&domain=microsoft.com` |
| Spotify | Own WordPress REST (`animal` namespace) | Own adapter | `GET api.lifeatspotify.com/wp-json/animal/v1/job/search` (one response, all jobs) | 67 (27 engineering) | No (detail pages `/jobs/{slug}` server-rendered) |
| Uber | Own API behind Cloudflare | Own adapter (httpx passes; curl TLS fingerprint challenged) | `GET jobs.uber.com/api/jobs/search/?search={q}&page={n}&pageSize=10`; empty search enumerates all | 508 | Yes (full HTML `Description` + `Salary.Description` range text in list response) |
| Atlassian | Own endpoint | Own adapter | `GET www.atlassian.com/endpoint/careers/listings` (one response, all jobs) | 243 | Yes (`overview` HTML in list response) |
| Oracle | Oracle Recruiting Cloud REST | Own adapter | `GET eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values&finder=findReqs;siteNumber=CX_45001,limit=24,offset={n},sortBy=POSTING_DATES_DSC` | 2239 | Not in list; separate requisition detail endpoint exists |
| Bloomberg | Avature | Own adapter (server-rendered HTML parse) | `GET bloomberg.avature.net/careers/SearchJobs/?listFilterMode=1&jobRecordsPerPage=12&jobOffset={n}` — server caps page size at 12; 374 total ⇒ ~32 pages (poolable) | 374 | No (list pages only; JobDetail pages server-rendered) |
| Snap | **Workday tenant** (also own API) | **Seed only — existing Workday adapter** | `POST wd1.myworkdaysite.com/wday/cxs/snapchat/snap/jobs` → 177; alternate own API `GET careers.snap.com/api/jobs` (177, no descriptions) | 177 | No |
| X (careers.x.com → x.ai, "SpaceXAI & X Platform") | **Greenhouse board `xai`** | **Seed only — existing Greenhouse adapter** | `GET boards-api.greenhouse.io/v1/boards/xai/jobs` → 252 (matches site's "252 OPEN ROLES") | 252 | Greenhouse detail API (existing pattern) |
| Tesla | Own site | **Blocked** — `GET www.tesla.com/cua-api/apps/careers/state` returns all 8084 listings in one JSON (id/title/dept/location lookups) but Akamai bot-manager challenges plain clients: curl 403 → 429 `{"cpr_chlge":"true"}` even with full browser headers; only a real browser passes | — | — |
| Shopify | Ashby (private board) + own brochure pages | Own adapter, hardest parse (or defer — user call) | `GET www.shopify.com/careers` (plain curl 200) embeds all **113** jobs (title, Ashby `ashby_jid`, publishedDate, location ids, compensation) in a `window.__reactRouterContext.streamController.enqueue(...)` JSON stream; per-job pages `/careers/{slug}_{jid}` and public `jobs.ashbyhq.com/shopify/{jid}` (200) hold descriptions | 113 | Yes, on per-job pages (extra fetch per job) |

Notes:

- **Microsoft**: the doc's earlier `gcsservices.careers.microsoft.com` endpoint is dead —
  the host serves a `*.azureedge.net` cert (common-name mismatch). The live API is the
  PCSx one above; no CSRF needed for plain curl. Apply URL: `positionUrl` is
  `/careers/job/{id}` on `apply.careers.microsoft.com` (verified 200). Search params:
  `q`/`query` keyword, `start` offset, `pgSz` page size; response `data.count` + `data.positions`
  (id, displayJobId/atsJobId, name, standardizedLocations, department, postedTs).
- **Uber**: curl is Cloudflare-challenged ("Just a moment…") but httpx 200s with a browser
  UA — our adapter stack (httpx) works; worth an adapter note so nobody "fixes" it to curl.
- **X**: careers.x.com now redirects to `x.ai/careers` (xAI/X merger); its open-roles page
  (252 roles) links exclusively to `job-boards.greenhouse.io/xai/jobs/*`, and the
  Greenhouse boards-api confirms 252. Seeding `xai` as Greenhouse covers it.
- **Snap**: Snap's own API and its Workday board agree on 177 postings; Workday adapter
  already handles `total`-driven pagination, so seed `snapchat/snap` as Workday (same
  shape as NVIDIA/Salesforce in T43). No new `SourceKind`.
- **Bloomberg**: pagination params discovered from the page's own links:
  `?listFilterMode=1&jobRecordsPerPage=N&jobOffset=O` (N ignored, effectively 12);
  `jobOffset >= total` returns empty (clean overflow). An RSS feed
  (`SearchJobs/feed/`) also exists but is page-capped the same way.
- **Oracle**: `finder=findReqs` returns facets only unless `expand=requisitionList.secondaryLocations`
  is passed — the job rows live in `items[0].requisitionList`. Fields include Id, Title,
  PostedDate, PrimaryLocation; detail/apply URL is built from the requisition Id
  (`careers.oracle.com` job page).
- **Shopify**: Greenhouse/Lever/Ashby public boards all 404; sitemap has no listing pages;
  the landing page's embedded stream is the only structured source. Parse is feasible
  (stable string fields around each `ashby_jid`) but it is the most fragile of the batch —
  flag for user decision before building.
- **Tesla**: the only fully scraper-hostile target besides Google. The listing API shape
  is excellent (single JSON, `lookup` tables resolving department/location ids) but the
  Akamai challenge (`cpr_chlge`) cannot be passed without browser-grade TLS+JS. Uncovered
  unless the user reconsiders headless browsers.

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
