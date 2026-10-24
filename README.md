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

Vehicle search (`GET /api/vehicles/search`) applies every supplied filter together (AND). Its open choices were resolved as follows:

- `make` and `model` match case-insensitively anywhere in the value, so `xuv` and `700` both find `XUV700`. `%` and `_` in a term are matched literally rather than as wildcards.
- Text terms are trimmed; an empty or whitespace-only term is ignored, so a cleared form field means "no filter".
- `category` accepts a single value from the controlled vocabulary; any other value returns `422`.
- `min_price` and `max_price` are inclusive, must be non-negative with at most two decimal places, and `min_price` greater than `max_price` returns `422`.
- With no filters, search returns every active listing. Out-of-stock listings are included so the SPA can show them with a disabled Purchase button.
- Paging and ordering match `GET /api/vehicles`: `page`, `page_size` (default 20, capped at 100), newest first, with `total` counting all matches.
- Any authenticated user may search. No trigram index is added for substring matching; at dealership catalogue sizes a sequential scan is fast, and a `pg_trgm` GIN index is the scaling follow-up.

Vehicle update (`PUT /api/vehicles/{id}`) resolves its open choices as follows:

- Only Administrators may update listings. The kata marks only delete and restock as admin-only, but its frontend section places update in the admin UI and the domain gives Standard Users no inventory-management authority, so a Standard User receives `403`.
- The request is a full replacement: `make`, `model`, `category`, and `price` are all required and follow the same rules as creation.
- `quantity` and any other unknown field return `422`; stock changes only through audited purchase and restock operations.
- An unknown listing ID returns `404`; a malformed ID returns `422` for the `listing_id` field.
- Success returns `200` with the updated listing. `updated_at` is refreshed on every update while `id`, `created_at`, and quantity are unchanged, so newest-first ordering is unaffected by edits.
- Concurrent administrator edits are last-write-wins. Because updates never touch quantity, they cannot lose a concurrent purchase or restock; optimistic locking is a possible future addition.

Vehicle deletion (`DELETE /api/vehicles/{id}`) is a soft delete, as recorded in ADR 0008. Its open choices were resolved as follows:

- Only Administrators may delete. Success returns `204 No Content`.
- The row is kept with its remaining quantity. `deleted_at` and `deleted_by` record when and by whom; a database check requires both to be set together, and `deleted_by` references the account with `ON DELETE RESTRICT`.
- Deleted listings disappear from list and search. Updating, or deleting again, returns `404`, and a second delete never rewrites the original deletion record. An unknown ID also returns `404`; a malformed ID returns `422`.
- Concurrent deletes are resolved by a single conditional `UPDATE ... WHERE deleted_at IS NULL`: the first wins and the other receives `404`.
- No partial index for active listings is added yet; `(created_at DESC, id DESC) WHERE deleted_at IS NULL` is the scaling follow-up. Restoring a deleted listing is out of scope.

Vehicle purchase (`POST /api/vehicles/{id}/purchase`) buys exactly one unit and takes no request body (ADR 0007). Its open choices were resolved as follows:

- Any authenticated account may purchase, Administrators included; ADR 0007 and the glossary were updated to say so.
- Success returns `200` with the updated listing, so the SPA can refresh the card and disable Purchase at zero. A purchase does not change the listing's `updated_at`, which tracks catalogue edits only.
- Each purchase stores a durable record in `purchases` with the purchaser and snapshots of price, make, model, and category. Later edits never change those snapshots. Both foreign keys use `ON DELETE RESTRICT`, and `purchaser_id` is indexed for a future "my purchases" view.
- An out-of-stock listing returns `409 out_of_stock`; a missing or deleted listing returns `404`.
- Stock is decremented by a single conditional `UPDATE ... WHERE quantity > 0 AND deleted_at IS NULL` in the same transaction as the purchase insert. A concurrency test fires 20 simultaneous purchases at a stock of 5 and expects exactly 5 successes, 15 conflicts, a final quantity of 0, and 5 purchase records. The commit history shows the naive read-then-write version failing that test (all 20 succeeded) before the atomic fix.

## My AI Usage

I used OpenAI Codex to facilitate a structured architecture review before implementation. It helped compare the FastAPI/PostgreSQL stack, identify authorization and inventory edge cases, and record the resulting glossary and architecture decisions. I reviewed and selected each decision, including the explicit duplicate-email trade-off; AI accelerated the design discussion while the final scope choices remained mine.

I will also use Codex with the repository's `tdd-red-green-refactor` workflow during implementation. It will help turn each agreed behavior into one failing test, the smallest passing implementation, and—only when valuable—a refactor, while I verify test failures, review generated code, and retain the resulting Git history. Every AI-assisted commit will include the required co-author trailer, and this repository's `PROMPTS.md` retains the raw chat record.

I also used OpenAI Codex to package my red-green-refactor requirements as a repository skill and connect it to `AGENTS.md`. This gives future implementation work a concrete sequence for tests, code, commits, and verification. The workflow came from my requirements; Codex handled the skill formatting and repository wiring.

I used OpenAI Codex to scaffold the non-feature foundations: the FastAPI/Alembic project, PostgreSQL Docker configuration, Testcontainers fixture design, safe structured logging, and the Vite/React toolchain. I reviewed the resulting settings, commands, and test coverage before committing; Codex sped up the repetitive setup while the feature behavior remains reserved for the documented red-green-refactor sequence.

I used Claude Code (Anthropic) to analyse the repository state and suggest the next feature, then to interview me one question at a time on the vehicle search design: substring versus prefix matching, blank input, price bound semantics, category cardinality, out-of-stock visibility, access, indexing, and how to slice the work into TDD cycles. It offered a recommended answer for each question and I made the final calls. It then implemented search through separate red and green commits per behavior (inclusive price bounds, inverted range rejection, invalid filter values, blank terms, literal wildcards) and a final refactor sharing the page query with the list endpoint, running the full suite before every green and refactor commit. The question-by-question format surfaced edge cases, such as `%` in a search term matching everything, that I would otherwise have found later.

I repeated that process with Claude Code for vehicle update, deciding access, full versus partial replacement, unknown-field handling, malformed IDs, concurrency, and the response shape before any code was written. It drove four red-green cycles (full replacement, unknown listing 404, rejected extra fields such as `quantity`, malformed ID 422), added guard tests for rules that could not honestly start red, such as field validation and the administrator requirement, and finished with refactors that share catalogue validation between create and update.

For soft delete, Claude Code interviewed me on the response code, repeat deletes, the audit schema, concurrent deletes, and indexing, then drove five red-green cycles: soft deletion with its audit columns (migration 0005), hiding deleted listings from list and search, unknown-ID 404, repeat-delete 404 that preserves the original audit, and update-after-delete 404. It also checked the new migration's downgrade and upgrade against a disposable PostgreSQL container. One concrete catch: its first migration revision ID exceeded Alembic's 32-character version column, which the test suite exposed immediately.

For purchase, the Claude Code interview covered who may buy (I chose to let Administrators purchase and had ADR 0007 updated to match), the response code, the purchases schema, whether a sale counts as an edit, and how to tell the concurrency story honestly. It built the endpoint with a deliberately naive read-then-write decrement, added the purchase record, out-of-stock and not-found cycles, and a rollback guard that uses a temporary database trigger to make the purchase insert fail. Its concurrency test then showed the naive code letting all 20 buyers take 5 units, and the atomic conditional `UPDATE` fixed it. Seeing the oversell reproduce made the value of the atomic statement concrete rather than theoretical.
