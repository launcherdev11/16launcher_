.PHONY: help sync pre-commit setup run test lint fmt build dist install-app check-deps

help:
	@echo Available commands:
	@echo * sync           - Sync dependencies
	@echo * pre-commit     - Setup pre-commit hooks
	@echo * setup          - Full project setup (venv + deps + pre-commit)
	@echo * run            - Run application
	@echo * test           - Run tests with coverage
	@echo * lint           - Check code with ruff
	@echo * fmt            - Format code with ruff
	@echo * build          - Build project
	@echo * dist           - Create executable
	@echo * install-app    - Install application to system
	@echo * check-deps     - Check dependencies

sync:
	@echo "Syncing dependencies..."
	uv sync --all-groups
	@echo "Dependencies synced"

pre-commit:
	@echo "Setting up pre-commit hooks..."
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg
	@echo "Pre-commit hooks configured"

setup: sync pre-commit
	@echo "Project fully configured!"

run:
	@echo "Starting 16Launcher..."
	uv run src/main.py

test:
	@echo "Running tests..."
	uv run pytest

lint:
	@echo "Checking code..."
	uv run ruff check src/
	uv run mypy src/

fmt:
	@echo "Formatting code..."
	uv run ruff format src/
	uv run ruff check --fix src/

build:
	@echo "Building project..."
	uv run build
	@echo "Project built"

dist: build
	@echo "Creating executable..."
	uv run PyInstaller 16Launcher.spec
	@echo "Executable created"

install-app: build
	@echo "Installing application..."
	uv run pip install dist/*.whl
	@echo "Application installed"

check-deps:
	@echo "Checking dependencies..."
	uv run pip list
	@echo "Check completed"
