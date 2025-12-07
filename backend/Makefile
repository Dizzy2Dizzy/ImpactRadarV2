.PHONY: help migrate jobs.prices jobs.recompute jobs.alerts scanners scanners.loop scan-worker test lint verify verify.sources verify.integrity verify.scanners

help:
	@echo "ReleaseRadar Backend - Available Commands"
	@echo "=========================================="
	@echo "make migrate           - Run Alembic migrations (upgrade to head)"
	@echo "make jobs.prices       - Run nightly price backfill job"
	@echo "make jobs.recompute    - Recompute event statistics from price history"
	@echo "make jobs.alerts       - Run alert dispatcher job"
	@echo "make scanners          - Run all scanners once"
	@echo "make scanners.loop     - Run scanners continuously"
	@echo "make scan-worker       - Run manual scan job worker (processes queue)"
	@echo "make test              - Run pytest test suite"
	@echo "make lint              - Run code linters (ruff, mypy)"
	@echo ""
	@echo "Data Verification Commands:"
	@echo "make verify            - Run full verification suite (all checks)"
	@echo "make verify.sources    - Verify source URLs (check validity)"
	@echo "make verify.integrity  - Verify event data integrity"
	@echo "make verify.scanners   - Verify scanner output validation"

migrate:
	@echo "Running database migrations..."
	cd releaseradar && alembic upgrade head

jobs.prices:
	@echo "Running price backfill job..."
	python3 -m jobs.fetch_prices

jobs.recompute:
	@echo "Recomputing event statistics..."
	python3 -m jobs.recompute_event_stats

jobs.alerts:
	@echo "Running alert dispatcher..."
	python3 -m jobs.dispatch_alerts

scanners:
	@echo "Running all scanners once..."
	python3 jobs/run_scanners.py

scanners.loop:
	@echo "Running scanners continuously (10 min interval)..."
	python3 jobs/run_scanners.py --loop --interval 600

scan-worker:
	@echo "Starting manual scan job worker..."
	python3 jobs/scan_worker.py

test:
	@echo "Running test suite..."
	pytest -v --cov=. --cov-report=term-missing

lint:
	@echo "Running linters..."
	ruff check . --fix
	mypy . --ignore-missing-imports

verify:
	@echo "Running comprehensive verification suite..."
	python3 tools/run_full_verification.py

verify.sources:
	@echo "Verifying event source URLs..."
	python3 tools/verify_event_sources.py

verify.integrity:
	@echo "Verifying event data integrity..."
	python3 tools/verify_event_integrity.py

verify.scanners:
	@echo "Verifying scanner output..."
	python3 tools/verify_scanner_output.py
