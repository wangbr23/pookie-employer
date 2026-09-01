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

-BashPython 3.12+ installed (recommended via `pyenv` or system Python).

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