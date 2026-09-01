# Clean Code Conventions

Project-specific coding standards for agents and humans. Keep this practical and update it when conventions become clear from real work.

## Core principles

- Prefer simple, direct solutions over clever abstractions.
- Keep changes small, focused, and reviewable.
- Optimize for readability and maintainability before novelty.
- Do not introduce abstractions until there are at least two real call sites or a clear present need.
- Surface ambiguity, conflicting requirements, or risky tradeoffs instead of guessing silently.

## Reviewable changes

- Optimize for small diffs that a human can review, understand, and commit independently.
- Do not batch unrelated changes into one task.
- Keep feature work, refactors, dependency setup, and mechanical changes separate unless the combined change is tiny.
- If the implementation grows beyond the task's reviewable scope, stop and suggest a split instead of pushing through.

## Structure

- Avoid god files and oversized components/modules.
- Put reusable logic in the project's established `lib`/`utils`/service layer once reuse is real.
- Keep code close to where it is used until it has a reason to move.
- Prefer explicit names that describe domain intent over generic names like `data`, `item`, or `helper`.
- Keep the service boundary explicit: `frontend/` owns presentation and user interaction; `backend/` owns APIs, database writes, ingestion, ranking, and AI integration.
- Do not duplicate backend business rules in the frontend beyond presentation labels and lightweight form validation.

## Type safety

- Avoid `any`, broad casts, non-null assertions, and ignored type errors unless there is a documented reason.
- Model domain states explicitly instead of relying on loose objects or sentinel values.
- Validate external input at boundaries.
- Use TypeScript types for frontend API responses and Pydantic schemas for FastAPI request/response boundaries.
- Keep FastAPI OpenAPI output as the source of truth for backend API contracts once endpoint shapes exist.

## Error handling

- Handle expected failures deliberately.
- Do not swallow errors silently.
- Return or throw errors in the style already used by the project.
- Include enough context for debugging without leaking secrets or sensitive data.

## Testing

- Add or update tests for behavior changes when the project has a test setup.
- Prefer behavior-focused tests over brittle implementation tests.
- If tests cannot be run or do not exist yet, say so in the final report.
- Backend behavior changes should normally include pytest coverage.
- Frontend automated tests are not configured yet; until they are, run lint/typecheck/build for frontend changes and manually describe UI verification.

## Stop conditions

Stop and report instead of guessing or expanding scope if work requires:

- an unresolved product or architecture decision;
- credentials, accounts, or external approvals;
- a large unexpected refactor;
- unclear security/privacy implications;
- changes too broad for a human to review comfortably.

## Cleanup before finishing

- Remove dead code, debug logging, commented-out experiments, and unused imports.
- Do not leave TODO/FIXME comments unless they describe a real follow-up task also recorded in `TODO.md`.
- Run the relevant format/lint/typecheck/test commands from `AGENTS.md` when available.
