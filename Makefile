.PHONY: help setup fmt lint typecheck test run seed migrate upgrade scanners clean

help:  ## Show this help message
	@echo "ReleaseRadar - Makefile Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Install dependencies and set up development environment
	pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

fmt:  ## Format code with black and isort
	black releaseradar/ tests/
	isort releaseradar/ tests/

lint:  ## Lint code with ruff
	ruff check releaseradar/ tests/

typecheck:  ## Type check with mypy
	mypy releaseradar/

test:  ## Run tests with coverage
	pytest releaseradar/tests/ -v --cov=releaseradar --cov-report=term-missing --cov-report=html

test-unit:  ## Run only unit tests
	pytest releaseradar/tests/unit/ -v

test-integration:  ## Run only integration tests
	pytest releaseradar/tests/integration/ -v

run:  ## Run the Streamlit application
	streamlit run releaseradar/ui/streamlit_app.py --server.port 5000

run-legacy:  ## Run the legacy app.py (deprecated)
	streamlit run app.py --server.port 5000

seed:  ## Seed database with initial data
	python -m releaseradar.db.seed

migrate:  ## Create a new Alembic migration
	alembic -c releaseradar/db/alembic.ini revision --autogenerate -m "$(message)"

upgrade:  ## Apply pending Alembic migrations
	alembic -c releaseradar/db/alembic.ini upgrade head

downgrade:  ## Rollback one Alembic migration
	alembic -c releaseradar/db/alembic.ini downgrade -1

scanners:  ## Run scanners manually (SEC, FDA, Company Releases)
	python -m releaseradar.tasks.run_scanners

scheduler:  ## Start the background scheduler
	python -m releaseradar.tasks.scheduler

clean:  ## Clean up cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -f .coverage

check: lint typecheck test  ## Run all checks (lint, typecheck, test)

ci: check  ## Run CI pipeline locally

.DEFAULT_GOAL := help
