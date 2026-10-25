.PHONY: db-up db-down migrate seed-admin seed-demo test-backend test-frontend e2e lint report requirements

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

seed-admin:
	cd backend && uv run python -m app.scripts.seed_admin

seed-demo:
	cd backend && uv run python -m app.scripts.seed_demo

test-backend:
	cd backend && uv run pytest --cov=app --cov-report=term-missing --cov-report=html --junitxml=reports/junit.xml

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npm run e2e

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint && npm run format:check

# Overwrites docs/test-report.md; failing suites are recorded rather than aborting the report.
report:
	-cd backend && uv run pytest -q --cov=app --cov-report= --junitxml=reports/junit.xml
	cd backend && uv run coverage report --format=markdown > reports/coverage.md
	-cd frontend && npx vitest run --reporter=default --reporter=json --outputFile.json=reports/vitest.json
	python3 scripts/test_report.py

# Vercel installs the API from this file; regenerate it whenever backend/uv.lock changes.
requirements:
	uv export --project backend --frozen --no-dev --no-hashes --no-annotate --format requirements-txt -o requirements.txt
