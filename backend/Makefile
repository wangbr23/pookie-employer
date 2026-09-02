.PHONY: install dev run test lint format typecheck seed alembic-help alembic-current alembic-revision alembic-upgrade alembic-downgrade help

VENV = venv
SYSTEM_PYTHON = python3
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn
PYTEST = $(VENV)/bin/pytest
BLACK = $(VENV)/bin/black
RUFF = $(VENV)/bin/ruff
MYPY = $(VENV)/bin/mypy
ISORT = $(VENV)/bin/isort

help:
	@echo "Available commands:"
	@echo "  make install         - install production dependencies"
	@echo "  make dev             - install development dependencies"
	@echo "  make run             - run the FastAPI server with reload"
	@echo "  make test            - run tests with pytest"
	@echo "  make lint            - run ruff linting"
	@echo "  make format          - format code with black and isort"
	@echo "  make typecheck       - run mypy type checking"
	@echo "  make seed            - seed the database with an initial profile and sources"
	@echo "  make alembic-help    - show alembic help"
	@echo "  make alembic-current - show current database revision"
	@echo "  make alembic-revision - create a new migration revision"
	@echo "  make alembic-upgrade - upgrade database to latest revision"
	@echo "  make alembic-downgrade - downgrade database revision"

install: $(VENV)/bin/activate
	$(PIP) install -r requirements.txt

dev: $(VENV)/bin/activate
	$(PIP) install -e .[dev]

$(VENV)/bin/activate:
	$(SYSTEM_PYTHON) -m venv $(VENV)

run:
	$(UVICORN) pookie_backend.main:app --reload

test:
	$(PYTEST)

lint:
	$(RUFF) check src tests

format:
	$(BLACK) src tests
	$(ISORT) src tests

typecheck:
	$(MYPY) src

seed:
	$(PYTHON) -m pookie_backend.seed

alembic-help:
	$(PYTHON) -m alembic --help

alembic-current:
	$(PYTHON) -m alembic current

alembic-revision:
	$(PYTHON) -m alembic revision --autogenerate -m "$(MESSAGE)"

alembic-upgrade:
	$(PYTHON) -m alembic upgrade head

alembic-downgrade:
	$(PYTHON) -m alembic downgrade -1
