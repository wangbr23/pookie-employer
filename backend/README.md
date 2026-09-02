# Backend

Python + FastAPI backend service for APIs and job-processing work.

## Responsibility

- API authorization and backend REST contracts.
- Domain database writes and migrations.
- Job source ingestion, crawl observability, normalization, deduplication, and ranking.
- AI provider integration, consent checks, cost metadata, and prompt/output redaction rules.
- Cron/CLI job entrypoints once implemented.

## Non-responsibility

- No dashboard rendering or frontend styling.

## Development

### Prerequisites

Python 3.12+ installed (recommended via `pyenv` or system Python).

### Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   For development, also install dev dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

   Alternatively, install using the pyproject.toml:

   ```bash
   pip install -e .[dev]
   ```

### Configuration

The backend loads typed settings from environment variables and validates required values at startup.

Required variables:

- `DATABASE_URL` — SQLAlchemy database URL, e.g. `postgresql+psycopg://postgres:postgres@localhost:5432/pookie_employer_dev`
- `SECRET_KEY` — secret value for future auth/session needs; use a strong local value and never commit it
- `PYTHON_ENV` — `development`, `test`, or `production` (`development` by default)

From the repo root, copy the template before running the backend:

```bash
cp .env.example .env
```

If you run commands from `backend/`, either export these variables in your shell or copy/link the root `.env` into `backend/.env` for local development. Do not commit `.env` files.

### Running the app

Start the FastAPI server with uvicorn:

```bash
uvicorn pookie_backend.main:app --reload
```

The server will be available at `http://localhost:8000`.

- Root endpoint: `GET /`
- Health endpoint: `GET /health`
- OpenAPI documentation: `GET /docs`

### Testing

Run tests with pytest:

```bash
pytest
```

For coverage:

```bash
pytest --cov=pookie_backend --cov-report=html
```

### Linting and formatting

Format code with black and isort:

```bash
black src tests
isort src tests
```

Lint with ruff:

```bash
ruff check src tests
```

Type checking with mypy:

```bash
mypy src
```

### Makefile convenience

A `Makefile` is provided with common commands:

- `make install` – install dependencies
- `make dev` – install dev dependencies
- `make run` – run the server with reload
- `make test` – run tests
- `make lint` – run lint checks
- `make format` – format code
- `make typecheck` – run mypy
- `make seed` – seed the database with one admin-configured profile and the initial approved source list (safe to rerun)

### Database migrations with Alembic

This project uses Alembic for database migrations. The following commands are available:

- `make alembic-help` – show alembic help
- `make alembic-current` – show current database revision
- `make alembic-revision MESSAGE="migration message"` – create a new migration revision
- `make alembic-upgrade` – upgrade database to latest revision
- `make alembic-downgrade` – downgrade database revision

Alembic automatically imports database settings from the application configuration.

## Project structure

```
backend/
├── pyproject.toml           # Project metadata and dependencies
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── README.md                # This file
├── Makefile                 # Convenience commands
├── src/
│   └── pookie_backend/
│       ├── __init__.py
│       └── main.py          # FastAPI app and routes
└── tests/
    ├── conftest.py          # Pytest fixtures
    └── test_main.py         # Tests for main endpoints
```

## Next steps

See `TODO.md` for upcoming tasks, including database configuration, authentication, and API endpoints.