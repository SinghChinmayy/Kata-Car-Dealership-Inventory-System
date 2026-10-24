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

Vehicle restock (`POST /api/vehicles/{id}/restock`) adds stock and records a Stock Adjustment (ADR 0009). Its open choices were resolved as follows:

- Only Administrators may restock. The body is `{"quantity": n}`: required, a whole number of at least 1, with no other fields allowed. There is no per-request cap, but a restock that would push stock past PostgreSQL's `INTEGER` limit returns `422` on `quantity` instead of failing in the database.
- Success returns `200` with the updated listing. Like a purchase, a restock leaves `updated_at` unchanged.
- Each restock inserts a `stock_adjustments` row (listing, administrator, quantity, time) in the same transaction as the increment. Both foreign keys use `ON DELETE RESTRICT`, and `listing_id` is indexed for a future per-listing stock history.
- A missing or deleted listing returns `404`.
- The increment is a single relative `UPDATE ... SET quantity = quantity + :n`, so it cannot lose a concurrent purchase or restock. A guard test races 10 restocks against 10 purchases from zero stock and checks that stock always matches the purchase and adjustment records.
- The kata's admin UI lists only add, update, and delete. The SPA adds a per-listing restock control as well, because otherwise this endpoint could not be reached from the UI.

The single-page app resolves the frontend's open choices as follows:

- Routes are `/login`, `/register`, and a protected `/` dashboard. Anonymous visitors and unknown paths go to sign in; signed-in visitors skip the sign-in and registration pages. Registration signs the new account straight in.
- The access token is held in memory only (ADR 0003), so a browser refresh requires signing in again. Any `401` on a signed-in request ends the session, clears cached data, and returns to sign in with a notice.
- The SPA calls relative `/api` paths. In development Vite proxies them to FastAPI on port 8000; `VITE_API_BASE_URL` can point elsewhere for split hosting.
- The dashboard always uses the search endpoint. Submitted filters and the page number live in the URL, so back and forward keep them. Categories come from the API. Server validation errors appear beside the matching input.
- Each vehicle card shows the category, the INR price with Indian digit grouping (for example `₹12,50,000.00`), and the stock. Purchase happens in one click with no confirmation; the button is disabled at zero stock and while its request is in flight. A sold-out conflict is announced and the results refresh.
- Administrators see an Administrator badge, an Add vehicle button, and Edit, Restock, and Delete actions on each card. These open modal dialogs. Edit never sends quantity, and the delete confirmation focuses Cancel first.
- The design is a dark "showroom" theme with a single amber accent and a responsive one-to-three column grid.
- Component tests use Vitest, Testing Library with `user-event`, and MSW, which fails any test that makes an unexpected request. The single Playwright end-to-end journey is planned as a separate step.

## My AI Usage

I used OpenAI Codex to facilitate a structured architecture review before implementation. It helped compare the FastAPI/PostgreSQL stack, identify authorization and inventory edge cases, and record the resulting glossary and architecture decisions. I reviewed and selected each decision, including the explicit duplicate-email trade-off; AI accelerated the design discussion while the final scope choices remained mine.

I will also use Codex with the repository's `tdd-red-green-refactor` workflow during implementation. It will help turn each agreed behavior into one failing test, the smallest passing implementation, and—only when valuable—a refactor, while I verify test failures, review generated code, and retain the resulting Git history. Every AI-assisted commit will include the required co-author trailer, and this repository's `PROMPTS.md` retains the raw chat record.

I also used OpenAI Codex to package my red-green-refactor requirements as a repository skill and connect it to `AGENTS.md`. This gives future implementation work a concrete sequence for tests, code, commits, and verification. The workflow came from my requirements; Codex handled the skill formatting and repository wiring.

I used OpenAI Codex to scaffold the non-feature foundations: the FastAPI/Alembic project, PostgreSQL Docker configuration, Testcontainers fixture design, safe structured logging, and the Vite/React toolchain. I reviewed the resulting settings, commands, and test coverage before committing; Codex sped up the repetitive setup while the feature behavior remains reserved for the documented red-green-refactor sequence.

I used Claude Code (Anthropic) to analyse the repository state and suggest the next feature, then to interview me one question at a time on the vehicle search design: substring versus prefix matching, blank input, price bound semantics, category cardinality, out-of-stock visibility, access, indexing, and how to slice the work into TDD cycles. It offered a recommended answer for each question and I made the final calls. It then implemented search through separate red and green commits per behavior (inclusive price bounds, inverted range rejection, invalid filter values, blank terms, literal wildcards) and a final refactor sharing the page query with the list endpoint, running the full suite before every green and refactor commit. The question-by-question format surfaced edge cases, such as `%` in a search term matching everything, that I would otherwise have found later.

I repeated that process with Claude Code for vehicle update, deciding access, full versus partial replacement, unknown-field handling, malformed IDs, concurrency, and the response shape before any code was written. It drove four red-green cycles (full replacement, unknown listing 404, rejected extra fields such as `quantity`, malformed ID 422), added guard tests for rules that could not honestly start red, such as field validation and the administrator requirement, and finished with refactors that share catalogue validation between create and update.

For soft delete, Claude Code interviewed me on the response code, repeat deletes, the audit schema, concurrent deletes, and indexing, then drove five red-green cycles: soft deletion with its audit columns (migration 0005), hiding deleted listings from list and search, unknown-ID 404, repeat-delete 404 that preserves the original audit, and update-after-delete 404. It also checked the new migration's downgrade and upgrade against a disposable PostgreSQL container. One concrete catch: its first migration revision ID exceeded Alembic's 32-character version column, which the test suite exposed immediately.

For purchase, the Claude Code interview covered who may buy (I chose to let Administrators purchase and had ADR 0007 updated to match), the response code, the purchases schema, whether a sale counts as an edit, and how to tell the concurrency story honestly. It built the endpoint with a deliberately naive read-then-write decrement, added the purchase record, out-of-stock and not-found cycles, and a rollback guard that uses a temporary database trigger to make the purchase insert fail. Its concurrency test then showed the naive code letting all 20 buyers take 5 units, and the atomic conditional `UPDATE` fixed it. Seeing the oversell reproduce made the value of the atomic statement concrete rather than theoretical.

Before restock, I asked Claude Code to cross-reference the endpoint against the kata brief, ADRs, glossary, and TDD skill, which separated what was already decided from what was still open. The interview then settled the request body, limits (I chose no per-request cap), response, schema, concurrency proof, and the missing admin UI control. Claude Code drove four red-green cycles (restock, Stock Adjustment record with migration 0007, not-found, and integer-overflow rejection), plus guard tests for validation, authorization, rollback, and restocks racing purchases, then refactored the shared active-listing check and test trigger helper.

For the frontend, Claude Code read the existing toolchain and ADRs first, then interviewed me on test tooling (I approved adding MSW and `user-event`), API routing, routes, registration flow, session expiry, search UX, card and purchase behavior, admin dialogs, visual direction, and slicing. It built the SPA one red-green cycle per behavior: sign-in, the sign-in error, registration with auto sign-in, field errors, route guards, the listing grid, purchase, search filters, pagination, session expiry, admin-only controls, and the add, edit, delete, and restock dialogs. It then ran the real stack in a browser, which surfaced two layout issues that the component tests could not see: the filter buttons overflowing at mid widths, and Log out wrapping on phones. It also found that `.env.example`'s CORS value breaks settings parsing and that the admin seed command is still a placeholder.
