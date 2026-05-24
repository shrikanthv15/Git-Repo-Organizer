# Contributing to Git-Repo-Organizer

Thanks for taking a look. This is a small full-stack project, but we keep
the bar high on code clarity + test coverage. The fastest path to a
merged PR is to:

1. Run things locally before pushing
2. Match the existing code style (no surprises)
3. Keep the diff focused (one concern per PR)

## Local development

See [`HOW-TO-RUN.md`](HOW-TO-RUN.md) for the full setup. Quick path:

```bash
docker compose up --build      # everything (Postgres + Temporal + backend + worker + frontend)
```

Or 3-terminal dev (no Docker):

```bash
# Terminal 1
temporal server start-dev

# Terminal 2
cd backend && uv sync && uv run python -m app.temporal.worker

# Terminal 3
cd backend && uv run python -m app.main
```

Frontend dev server:

```bash
cd frontend && pnpm install && pnpm dev
```

## Running tests

Backend (pytest with coverage, run from repo root):

```bash
uv --project backend run pytest          # all tests, with coverage report
uv --project backend run pytest --no-cov # faster, skips coverage
uv --project backend run pytest tests/test_logging.py  # one file
```

Frontend (no test framework wired yet — coming in a future sprint).

## Code style

- **Backend (Python 3.12):** PEP 8 + type hints on function signatures. We use `structlog` for logging — never `print()` or `logging.basicConfig` in app code. Bind context via `temporal_activity_context()` (Temporal) or `LoggingMiddleware` (FastAPI) so log lines carry `workflow_id`/`request_id`/etc.
- **Frontend (TypeScript + Next.js 16):** App Router conventions. `"use client"` only when you actually need client-side state. Tailwind utility classes via `cn()` from `@/lib/utils`. shadcn/ui primitives for buttons, sheets, scroll areas — don't roll your own.
- **No file >250 LOC** without strong justification. Split by concern.
- **Conventional commits** for PR titles: `feat(scope): …`, `fix(scope): …`, `refactor(scope): …`, `docs(scope): …`.

## PR style

- **Title:** under 70 chars, conventional-commit prefix.
- **Body:** lead with a Summary; describe what changed + why (link issues if any); list verification (tests passed? build clean?).
- **Per-hero commits:** if the change came from the OpenClaw JL pipeline, keep individual hero commits (no squash). Otherwise normal squash is fine.
- **No `git push --force` to `main`.** Open a fresh PR or `git revert`.

## Filing an issue

Use GitHub Issues. For bugs, include:
- What you did
- What happened
- What you expected
- Console / log output if relevant

For feature requests, include the user-facing problem you're trying to
solve. Code-level proposals welcome but optional.

## Code review

The maintainer ([@shrikanthv15](https://github.com/shrikanthv15)) reviews
every PR. CI runs lint + tests on push (when wired). PRs land via merge
commit (preserves the per-hero attribution from the build pipeline).
