# Car Dealership Inventory System

## Local development

This repository is a small monorepo: `backend/` contains the FastAPI API and Alembic migrations, and `frontend/` contains the React/Vite SPA. PostgreSQL runs in Docker; the API and SPA run on the host.

Prerequisites: Docker with a running daemon, [uv](https://docs.astral.sh/uv/), Node.js/npm, and Python 3.9 or newer.

```bash
cp .env.example .env
make db-up
cd backend && uv sync --all-groups && uv run alembic upgrade head
cd ../frontend && npm ci
```

Start the API with `cd backend && uv run uvicorn app.main:app --reload`, and the SPA with `cd frontend && npm run dev`. FastAPI's local OpenAPI documentation is available at `http://localhost:8000/docs`; `GET /health` verifies database readiness.

Common commands are exposed through the root `Makefile`: `make migrate`, `make test-backend`, `make test-frontend`, and `make lint`. Backend integration tests start one disposable PostgreSQL Testcontainers instance, migrate it once per session, and truncate application tables between tests. Docker must be running for that suite.

## Security scope and trade-offs

User registration normalizes email by trimming and lowercasing it, validates it as an email address, and protects it with a database unique index. A duplicate registration returns `409 Conflict`; this intentionally reveals that the email is already registered, an accepted trade-off for this kata. Login failures always return a generic `401 Unauthorized` response.

The project does not apply provider-specific email rules such as removing Gmail dots or `+` tags, because those transformations can merge distinct identities. Email verification, password reset, and profile fields are intentionally out of scope.

JWT access tokens contain only the account UUID and standard issuance/expiry claims. Each protected request therefore performs one database lookup to load the current account and role. That small per-request cost is deliberate: role changes take effect immediately instead of waiting for a role embedded in an existing token to expire.

Login and registration rate limiting is deferred. An in-process limit would not be a reliable protection once the application has multiple instances, and this kata does not include the shared rate-limit infrastructure needed to make that guarantee. It is a production-hardening follow-up.

## Assumptions and additions

Listings are not required to be unique by make, model, category, or price. The system treats the listing ID as the only uniqueness guarantee because the kata intentionally does not model details such as VIN, year, or trim.

## My AI Usage

I used OpenAI Codex to facilitate a structured architecture review before implementation. It helped compare the FastAPI/PostgreSQL stack, identify authorization and inventory edge cases, and record the resulting glossary and architecture decisions. I reviewed and selected each decision, including the explicit duplicate-email trade-off; AI accelerated the design discussion while the final scope choices remained mine.

I will also use Codex with the repository's `tdd-red-green-refactor` workflow during implementation. It will help turn each agreed behavior into one failing test, the smallest passing implementation, and—only when valuable—a refactor, while I verify test failures, review generated code, and retain the resulting Git history. Every AI-assisted commit will include the required co-author trailer, and this repository's `PROMPTS.md` retains the raw chat record.

I also used OpenAI Codex to package my red-green-refactor requirements as a repository skill and connect it to `AGENTS.md`. This gives future implementation work a concrete sequence for tests, code, commits, and verification. The workflow came from my requirements; Codex handled the skill formatting and repository wiring.

I used OpenAI Codex to scaffold the non-feature foundations: the FastAPI/Alembic project, PostgreSQL Docker configuration, Testcontainers fixture design, safe structured logging, and the Vite/React toolchain. I reviewed the resulting settings, commands, and test coverage before committing; Codex sped up the repetitive setup while the feature behavior remains reserved for the documented red-green-refactor sequence.
