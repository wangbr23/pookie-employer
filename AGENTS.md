# Pookie Employer

AI job finder for my software engineer girlfriend to help her find jobs that suit her experience

## Stack
- Frontend language/runtime: TypeScript on Node.js
- Frontend framework: Next.js App Router
- Frontend package manager: npm
- Styling: Tailwind CSS
- Backend language/runtime: Python 3.12+
- Backend framework: FastAPI
- Database/ORM: PostgreSQL with SQLAlchemy 2.x and Alembic

## Commands
- Install frontend: `cd frontend && npm install`
- Install backend: `cd backend && make dev`
- Dev/run frontend: `cd frontend && npm run dev`
- Dev/run backend: `cd backend && make run`
- Test frontend: not configured yet
- Test backend: `cd backend && make test`
- Lint frontend: `cd frontend && npm run lint`
- Typecheck frontend: `cd frontend && npm run typecheck`
- Lint backend: `cd backend && make lint`
- Typecheck backend: `cd backend && make typecheck`
- Format backend: `cd backend && make format`
- Build frontend: `cd frontend && npm run build`
- Build backend: not applicable yet

## Conventions
Cross-project coding principles (KISS, no god files, surface conflicts, etc.) live in your global agent instructions — don't restate them here. Project coding conventions live in `CLEANCODE.md`; keep detailed code-quality rules there so this file stays focused on project context.

This section is only for what's specific to *this* repo:
- Code style: keep frontend-only code under `frontend/`; keep backend/API/ingestion/ranking/database code under `backend/`; do not give the frontend direct database access.
- Testing approach: frontend tests are not configured yet; backend uses pytest. Add tests with backend behavior changes when practical.
- Commit message format: short imperative subject, optionally prefixed with the task id, e.g. `T6 add backend settings`.

## Architecture
Pookie Employer is a two-service monorepo:

- `frontend/` — Next.js dashboard. Owns presentation and user interactions only.
- `backend/` — FastAPI service. Owns API authorization, domain database writes, migrations, ingestion, normalization, dedupe, AI ranking, refresh jobs, and source observability.
- PostgreSQL is the shared persistence layer. Local Docker Postgres is development-only; production must use managed durable Postgres.

First milestone uses user-triggered on-demand refresh rather than daily cron. Refresh should target a 90-second UX budget with bounded source concurrency, timeouts, unchanged-job skipping, AI evaluation caps, partial results, and visible status. Daily scheduled refresh is deferred.

## Agent workflow

Agents should optimize for reviewable diffs: one coherent change per task, small enough for a human to understand before committing. If the work grows beyond that scope, stop and propose a split rather than continuing with a large, hard-to-review change.

### Standard project flow

For returning to an existing project, start with:

0. `project-status` — read context files, specs/designs, TODO, and git/worktree state; report the current state and recommended next step.

For new work, use this skill sequence:

1. `project-init` — create the project context scaffold.
2. `grill-me` — harden the product idea into `docs/specs/<slug>.md`.
3. `design-review` — turn the spec into `docs/designs/<date>-<slug>.md` with independent review.
4. `plan-tasks` — break the design into small, reviewable tasks in `TODO.md`.
5. `dispatch` — run one wave of ready implementation tasks in isolated worktrees.
6. `code-review` — review each implementation branch/diff before merge.
7. Human review — the human inspects and approves the diff.
8. `land-task` — merge the approved task, check off `TODO.md`, and optionally clean up the worktree.
9. `code-cleanup` — after several landed tasks or before a milestone, audit the whole codebase for drift, duplication, dead code, and reviewability problems.
10. `save-progress` — update journal, decisions, specs/designs, and TODO before ending the session.

After `project-status`, follow its recommended next step rather than assuming where the project left off.

## Context files
Keep these current — they're what gives any session or agent tool continuity without re-deriving history from scratch.

- **AGENTS.md** (this file) — stack, commands, repo-specific conventions, architecture. Update only when one of those actually changes; it should stay stable day to day.
- **CLAUDE.md** — pointer to this file only. Don't duplicate content into it.
- **CLEANCODE.md** — coding conventions agents should follow while editing code. Update when recurring code-quality preferences or project-specific patterns become clear.
- **docs/journal.md** — append-only session log. Never edit past entries; if something turns out wrong, say so in a new one.
- **docs/decisions.md** — append-only log of significant technical decisions (dependency choices, schema changes, rejected approaches), one entry per decision. Never edit past entries — a reversed decision gets a new entry that supersedes the old one.
- **docs/specs/** — product/spec decisions from grilling or other discovery work. These capture what/why before implementation design.
- **docs/designs/** — design documents, implementation plans, mockups, and research write-ups. One file per document; save the working version here rather than leaving it only in chat or artifact history.
- **.pi/skills/** — project-specific Pi skills. Keep them small, documented, and scoped to this repo's workflow.
- **TODO.md** — current and near-term work. The only file in this list meant to be edited freely rather than appended-only. Tasks carry an id, a manual/agent tag, and optional `depends-on` links so parallel-safe work can be computed rather than tracked by hand — see the `plan-tasks` skill.

**Before starting nontrivial work:** read this file, read CLEANCODE.md, skim the last few journal entries, check TODO.md.
**After finishing a session:** append a journal entry (what changed, why, what's next), update TODO.md, and append a decision entry if a decision worth remembering was made.
