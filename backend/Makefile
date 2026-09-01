.PHONY: install dev run test lint format typecheck help

VENV = venv
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
	@echo "  make install    - install production dependencies"
	@echo "  make dev       - install development dependencies"
	@echo "  make run       - run the FastAPI server with reload"
	@echo "  make test      - run tests with pytest"
	@echo "  make lint      - run ruff linting"
	@echo "  make format    - format code with black and isort"
	@echo "  make typecheck - run mypy type checking"

install: $(VENV)/bin/activate
	$(PIP) install -r requirements.txt

dev: $(VENV)/bin/activate
	$(PIP) install -r requirements-dev.txt

$(VENV)/bin/activate:
	python -m venv $(VENV)

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