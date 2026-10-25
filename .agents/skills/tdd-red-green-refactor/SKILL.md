---
name: tdd-red-green-refactor
description: Build this repository's application behavior one test at a time, with separate red, green, and optional refactor commits. Use for backend and frontend feature or bug-fix implementation.
---

# TDD red-green-refactor workflow

Build one small behavior at a time. Each phase is its own commit so the git history proves tests came before code.

## The cycle

1. **Red**: write ONE failing test for one behavior. Run it and confirm it fails for the intended reason (an assertion, not an import error or typo). Commit as `test: <behavior> (red)`. Touch only tests, plus minimal stubs if needed to import.
2. **Green**: write the minimum code that makes that test pass. Nothing extra. Commit as `feat: <behavior>` (or `fix:`). Put any migration the code needs in this commit, not in the red.
3. **Refactor**: improve structure with behavior unchanged and all tests green. Commit as `refactor: <what>`. Skip this commit if there is nothing worth cleaning.

## Rules

- One behavior per cycle. Never add many failing tests in one commit.
- A new test that passes immediately is not red. It is redundant or wrong; fix or drop it.
- Never squash, reorder, or rewrite history. The honest trail is the deliverable.
- Foundations (config, DB session, conftest fixtures, error envelope) are committed as `chore:`, not TDD cycles.
- Run the full suite before every green and refactor commit.

## Order of work

1. **Foundations**: config, DB session, test fixtures (real Postgres via testcontainers), error envelope.
2. **Auth**: register (hashes password, 409 on duplicate, ignores `role` in payload, password policy), login (token, generic 401), `get_current_user`, `require_admin`, demoted-admin loses access.
3. **Vehicle management**: create, list with pagination and `created_at DESC, id DESC` ordering, search (AND filters, 422s, route declared before `/{id}`), update (rejects `quantity`), soft delete (404 everywhere after).
4. **Purchase and restock**: atomic decrement, Purchase snapshot, StockAdjustment, rollback tests, then concurrency tests.
5. **Stretch (only after required work is green)**: `GET /api/purchases/me`, promote endpoint.
6. **Frontend**: start a screen only after its API endpoint is green. Component tests follow the same red/green commits, lighter in rigor. Playwright E2E is last, one journey only.

## Concurrency story (do this honestly)

1. Red: test fires 20 simultaneous purchases at stock of 5, expects exactly 5 successes, 15 x 409, final quantity 0.
2. Green (naive): read quantity, subtract 1, write. The test fails (oversell). Commit it as the naive attempt.
3. Fix: one atomic statement `UPDATE vehicles SET quantity = quantity - 1 WHERE id = :id AND quantity > 0 AND deleted_at IS NULL RETURNING ...`, with the Purchase insert in the same transaction. Test passes.

Use a separate DB session per request and a pool larger than the concurrency count, or the test proves nothing.

## AI usage requirements

- Every commit where an AI tool helped (including red commits with AI-written tests) ends with two blank lines then `Co-authored-by: <AI Tool Name> <tool address>` (Claude: `Claude <noreply@anthropic.com>`, Codex: `OpenAI Codex <codex@users.noreply.github.com>`; never a made-up `@users.noreply.github.com` address, GitHub credits the real account with that username). Add a short body line saying what the AI did and what was done manually.
- Keep raw, unedited chat logs or public chat links in a root `PROMPTS.md`. No summaries.
- README needs a detailed "My AI Usage" section: tools used, how they were used, and a reflection on the impact.

## Before finishing

- Generate the report: `pytest --cov=app --cov-report=term-missing --cov-report=html --junitxml=reports/junit.xml` and include it in the README.
- Add an "Assumptions and additions" section to the README listing every choice the spec left open.

## Commit message examples

```text
test: registering a duplicate email returns 409 (red)

feat: return 409 on duplicate email

refactor: extract email normalization helper


Co-authored-by: Claude <noreply@anthropic.com>
```
