.PHONY: db-up db-down migrate seed-admin seed-demo test-backend test-frontend e2e lint

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
