# Pookie Employer Spec

**Date:** 2026-08-31

**One-line description:** AI job finder for a software engineer that automatically discovers external jobs, ranks them against her experience and preferences, and presents trustworthy recommendations in a dashboard.

## Product goal

Pookie Employer should help one software engineer find jobs that suit her experience faster than manual browsing alone. The MVP is not a manual job-description analyzer; its utility depends on automated external job discovery from day one.

The product should optimize for:

- finding relevant roles she might otherwise miss;
- reducing time spent browsing job boards;
- explaining why a job is or is not a good fit;
- improving recommendations from her feedback.

## MVP scope

The MVP is a read-only recommender and review dashboard. It should discover jobs, rank them, explain fit, and link out to apply. It should not submit applications or represent the user externally.

In scope:

- Automated job discovery from external public/ATS/company sources.
- Resume-derived profile plus explicit preferences and dealbreakers.
- On-demand refresh for the first milestone; daily scheduled refresh is a later enhancement if proactive updates become useful.
- Fit buckets and explanations.
- Dashboard for viewing, filtering/searching, saving, dismissing, and opening apply links.
- Basic feedback loop through save/dismiss reasons and “more/less like this.”
- Coverage/debug visibility for searched sources, discovered jobs, and failures.
- Admin/source controls via config, seeds, or scripts at first.

Out of scope for MVP:

- Auto-applying.
- Resume or cover-letter generation.
- Application tracking pipeline.
- Interview prep.
- Recruiter outreach.
- Salary negotiation support.
- Browser extension.
- Mobile app.
- Multi-user SaaS, billing, or broad admin system.
- LinkedIn/Indeed auth scraping or hostile scraping.

## Job discovery and coverage

Jobs must come from external automated sources, not manual pasted descriptions. The initial source strategy is:

- multiple structured ATS platforms, such as Greenhouse, Lever, and Ashby where practical;
- a small curated company/source list;
- public company career pages where low-friction and allowed;
- search-engine/source-discovery expansion later, once the core pipeline works.

The target coverage goal is **near-exhaustive within a defined niche**, not internet-wide coverage. The niche should be defined from onboarding/profile constraints: role families, seniority, location/remote rules, industries, company types, and other preferences.

Breadth is a first-class product concern. The system should expose enough coverage information to understand what was searched and where gaps exist:

- last crawl time;
- number of sources searched;
- number of jobs discovered and new jobs found;
- source/platform/company coverage;
- source errors and repeated failures;
- AI-suggested new sources pending approval.

New domains suggested by AI require approval. Jobs from already-approved domains or source surfaces can be ingested automatically. Source management can start as config/database seeds and scripts; a polished admin UI can wait.

The product should avoid auth-gated sources, sources that explicitly prohibit scraping, bypassing anti-bot protections, and brittle/hostile scraping. Ambiguous sources should be reviewed case by case.

## User profile and onboarding

The real MVP should learn the user through resume upload plus a preference questionnaire. The first internal milestone may use a hardcoded/admin-configured profile to prove discovery, ranking, and dashboard value before building polished onboarding.

Required onboarding fields:

- target role titles/families;
- seniority range;
- remote/location constraints;
- work authorization constraints, if relevant;
- dealbreakers.

Optional onboarding fields:

- salary floor/range;
- preferred and avoided tech stacks;
- preferred and avoided industries;
- company size/stage preferences;
- nice-to-haves and interests;
- free-text notes.

Resume handling should minimize sensitive storage. The preferred MVP behavior is to use the uploaded resume to extract structured profile data, ask the user to confirm/edit it, then store structured profile data rather than the raw resume file unless a clear need emerges.

AI-generated profile fields, inferred preferences, hard filters, and source expansion suggestions require user/admin confirmation before affecting matching or crawling. AI-generated job summaries and rankings do not require pre-confirmation.

The app should avoid storing demographic data entirely. It should store only matching-relevant sensitive information. Work authorization should be represented as broad matching constraints, not detailed immigration history. Phone/address should not be stored unless necessary.

## Filtering, matching, and ranking

Hard filters should be reserved for constraints that make a job impossible or unacceptable, such as:

- location/remote incompatibility;
- work authorization incompatibility;
- clearance requirements;
- salary floor, if known and strict;
- seniority extremes.

Most other attributes should be ranking signals rather than hard filters to avoid over-filtering.

Ranking should initially consider:

- skill/resume match;
- preference match across role, industry, company type, remote/location, and salary;
- concern/gap score;
- freshness.

Over time, ranking should incorporate taste from feedback, such as saved/dismissed jobs and “more/less like this.” The system should not pretend to know application likelihood unless it has real signals.

Fit should be shown as qualitative buckets with explanations, not fake-precise percentages:

- Strong Fit;
- Possible Fit;
- Stretch;
- Needs Review.

Each recommendation should explain:

- why the job fits;
- matched skills/preferences;
- concerns, gaps, or uncertainty;
- what to verify before applying.

AI should be responsible for extracting structured job fields, matching/ranking against the profile, writing summaries and concerns, and generating source/search expansion ideas. AI should not generate application materials in MVP.

## Job records and lifecycle

For each discovered job, the system should store/show:

- title;
- company;
- location/remote information;
- source/apply link;
- full job description;
- parsed structured fields such as skills, seniority, salary, remote policy, and requirements;
- AI-generated fit summary and concerns;
- source and timestamps;
- application deadline or posting date if available.

Minimum fields before showing a job are title, company, apply link, and location. Low-confidence or incomplete jobs that pass minimum field requirements should not be silently hidden; they should appear separately as Needs Review.

Duplicates should be merged while preserving all source/apply links. This reduces dashboard clutter while keeping fallbacks if one source is stale or broken.

MVP job states:

- New;
- Seen;
- Saved;
- Dismissed;
- Possibly closed;
- Closed/archived.

There is no Applied state in MVP. The dashboard should include the original apply link so the user can apply externally.

If an apply link breaks, the system should:

- mark the job possibly closed;
- try preserved alternate source/apply links;
- re-search the company careers page for the role;
- surface a warning in the dashboard.

If a job is clearly closed, hide or archive it. If closure is uncertain, keep it visible with a “possibly closed” label.

Missing salary should not automatically exclude jobs. Missing salary should be marked unknown, ranked lower when relevant, and filterable. Missing remote/work-authorization details should surface uncertainty and rank lower or appear in Needs Review, rather than always being discarded unless contradicted by the post or strictness settings.

## Dashboard experience

A UI mock exists at `docs/specs/mocks/mock.png` and should be treated as visual direction for the warm, soft dashboard style unless superseded by later design work. The sample job content in the mock is illustrative, not product scope.

The MVP dashboard should be simple but usable, not production-polished. It should support:

- viewing ranked jobs;
- default view of new jobs since last visit, grouped by fit bucket;
- access to all active jobs, old jobs, saved jobs, dismissed/archived jobs, and possibly-closed jobs;
- filtering/searching;
- saving promising jobs;
- dismissing bad jobs with structured reasons;
- opening the original apply link.

The default view should emphasize new jobs since the last visit because job search is time-sensitive. Grouping by fit bucket means new jobs are organized into sections such as Strong Fit, Possible Fit, Stretch, and Needs Review. Old jobs remain accessible through other views and filters.

The initial feedback taxonomy should include:

Dismiss reasons:

- bad location/remote;
- wrong seniority;
- salary too low or missing;
- uninteresting company/industry;
- bad tech stack;
- too much missing experience;
- duplicate/stale;
- AI got this wrong;
- other/free text.

Save reasons:

- strong skill fit;
- interesting company/industry;
- good remote/location;
- good salary;
- growth/stretch opportunity;
- other/free text.

The product tone should be warm but professional. The project name can be affectionate, but recommendation explanations should feel trustworthy and clear rather than gimmicky.

## Privacy, access, and data control

Resume, preferences, salary, work authorization, employment history, and feedback are sensitive. If hosted anywhere, the product needs a real user account for access. No-auth is acceptable only if the app is strictly local/private.

Hosting and deployment are deferred to technical design, but the product constraints are:

- preserve privacy for sensitive profile and feedback data;
- third-party AI APIs are acceptable only with explicit consent;
- target ongoing MVP cost under $25/month;
- avoid storing unnecessary sensitive data.

The user should be able to delete/export data. MVP should support deletion of profile/resume-derived data, deletion of saved/dismissed job history, and export of saved jobs. Full profile/job feedback history export can come later if needed.

## Performance and reliability

Recommendations should generally be precomputed so the dashboard loads quickly. For the first milestone, crawling/ranking runs on demand when the user clicks Refresh jobs. The refresh should target completion within about 90 seconds by using bounded source concurrency, timeouts, unchanged-job skipping, AI evaluation caps, and partial results. Daily scheduled refresh is deferred until on-demand use proves valuable.

If some sources fail during a crawl, the system should show partial results, record source errors, retry failed sources later, and notify only for repeated failures. A failed source should not fail the whole crawl.

## First implementation milestone

The first valuable internal milestone is:

- hardcoded/admin-configured profile;
- external crawl from multiple structured ATS platforms plus a small curated company list;
- AI extraction/ranking/summaries;
- simple usable dashboard with filters, fit buckets, apply links, save/dismiss;
- basic coverage/debug view.

After this proves the discovery/ranking loop, the next milestone is real onboarding/profile editing through resume upload and preference questionnaire.

## Success criteria

The MVP is useful if it:

- saves time compared with manual job search;
- produces recommendations worth saving or applying to;
- finds jobs she would not have found herself;
- reduces junk results over time through feedback.

## Open questions for technical design

These are intentionally deferred from product grilling because they are implementation choices:

- exact language/runtime, framework, package manager, hosting, and database;
- whether crawling runs server-side, locally, or hybrid;
- exact ATS/source integrations for the first source set;
- authentication provider and deployment topology;
- AI provider/model choices and cost controls;
- schema and ranking implementation details.
