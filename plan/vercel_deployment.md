# Vercel Deployment Plan

Goal: ship the Car Dealership Inventory System (FastAPI + PostgreSQL API, React/Vite SPA) to Vercel with one public URL, a managed Postgres, and a repeatable migrate/seed step.

## 1. What the codebase already gives us

| Fact | Where | Deploy impact |
| --- | --- | --- |
| Every API route lives under `/api/*` (plus `/health`) | `backend/app/main.py` | SPA and API can share one origin. No CORS, no `VITE_API_BASE_URL`. |
| SPA calls `window.location.origin` unless `VITE_API_BASE_URL` set | `frontend/src/api/client.ts:23` | Same-origin works with zero frontend code change. |
| Module-level `app = create_app()` | `backend/app/main.py:681` | Vercel's Python runtime can serve it as an ASGI function. |
| Settings come from env vars; `.env` optional | `backend/app/core/config.py` | Set vars in Vercel dashboard; missing `.env` is fine. |
| `JWT_SECRET` validated at startup (>= 32 chars) | `config.py` | Missing secret = every request 500s. Must be set before first deploy. |
| Engine uses `pool_size=25, max_overflow=5` | `backend/app/db/session.py` | Too big for serverless: each warm instance could hold 30 connections. Needs change. |
| Migration 0008 needs `pg_trgm` | `alembic/versions/0008_trigram_search.py` | DB provider must allow `CREATE EXTENSION pg_trgm` (Neon and Supabase both do). |
| Token is in memory only, no cookies | ADR 0003 | Nothing extra for serverless; no session store needed. |
| Login rate limiting deferred | README | Public URL makes this a real risk; note it, optionally use Vercel Firewall rate-limit rule. |

## 2. Target architecture (recommended)

One Vercel project at repo root:

```
browser ──► https://<app>.vercel.app
              ├── /api/*, /health ──► Python function (FastAPI, api/index.py shim)
              └── everything else ──► static SPA (frontend/dist, fallback index.html)
                                         │
Python function ──► Neon Postgres (pooled URL, via Vercel Marketplace)
```

Why one project: same origin keeps ADR 0003's simple bearer flow, avoids CORS config, one deploy per commit, previews keep SPA and API in sync.

Considered and declined (2026-10-25): Vercel **Services**, which Vercel now recommends for a frontend plus a Python backend and which would drop `api/index.py` and `requirements.txt`. Declined because it is labelled Beta; the `/api` folder method is the older, supported path.

Alternative (not recommended): two projects (`frontend/` root and `backend/` root). Needs `VITE_API_BASE_URL` at build time and `ALLOWED_CORS_ORIGINS` per environment, and preview URLs break CORS unless wildcarded.

## 3. Database

- Provider: **Neon** through Vercel Marketplace (auto-injects `DATABASE_URL` and `DATABASE_URL_UNPOOLED`; supports `pg_trgm`; optional per-preview branches).
- Region: same as Vercel function region (e.g. both `bom1`/`ap-south-1` for an INR-market app, or both `iad1`/`us-east-1`).
- Runtime uses the **pooled** URL; migrations and seeding use the **unpooled** (direct) URL.
- Neon gives `postgres://...` URLs. SQLAlchemy needs `postgresql+psycopg://...`. Fix in code (normalize scheme in settings) so Marketplace-injected vars work untouched.

## 4. Code changes (each test-first, per AGENTS.md)

1. ✅ **DB URL normalization** — `config.py` rewrites `postgres://` / `postgresql://` to `postgresql+psycopg://`. Tested in `tests/test_config.py`.
2. ✅ **Serverless-friendly pool** — `session.py` takes its pool size from `DB_POOL_SIZE` (default 25 for local runs and the concurrency tests, at least 1; set `1` on Vercel). `max_overflow` stays 5, so at most 6 connections per instance on Vercel. Tested in `tests/test_session.py`.
3. ✅ **Prepared statements off** — psycopg gets `prepare_threshold=None` everywhere (one code path; negligible cost at this size), so statements are safe behind Neon's transaction pooler. Tested in `tests/test_session.py`.
4. ✅ **Vercel entry file** — `api/index.py` puts `backend/` on `sys.path` and exposes `app.main:app`. Tested by loading it from the repository root in a child process (`tests/test_vercel_entry.py`).
5. ✅ **Python deps for Vercel** — root `requirements.txt` from `make requirements` (`uv export --frozen --no-dev --no-hashes --no-annotate`): runtime packages only. A test fails if it drifts from `backend/uv.lock`.
6. ✅ **`vercel.json`** at repo root:
   - `"framework": null` (Other). Vercel docs: a detected Python framework preset takes over all requests and `api/` files stop being functions, and FastAPI in a root `requirements.txt` could trigger that.
   - Install and build the SPA from `frontend/`; serve `frontend/dist`.
   - Rewrites: `/api/(.*)` and `/health` → `/api/index` (the app still sees the original path); everything else → `/index.html`. Rewrites apply after static files, so `/assets/*` needs no exclusion.
   - `functions["api/index.py"].excludeFiles` drops frontend, docs, plan, scripts and backend tests/reports from the function bundle. No `maxDuration`: the default is enough.
   - Validated against Vercel's published schema; `vercel build` needs a linked project, so it runs at first deploy.

   `.python-version` at root pins Vercel to 3.12. Existing local `backend/.venv` (3.11) is untouched; a fresh `uv sync` would pick 3.12. `.vercelignore` keeps `.env`, virtualenvs, `node_modules`, build/test output, `.claude`, `.agents`, `design-samples`, `docs`, `plan` and `frontend/e2e` out of CLI uploads.
7. **Docs** — README "Deployment" section (env vars, migrate/seed commands, URLs); append Vercel usage to "My AI Usage"; append this chat to `PROMPTS.md`; ADR 0014 "Deploy to Vercel with Neon".

## 5. Environment variables (Vercel → Project → Settings)

| Var | Production | Preview | Note |
| --- | --- | --- | --- |
| `DATABASE_URL` | Neon pooled (auto) | Neon branch pooled (auto) | normalized in code |
| `JWT_SECRET` | `openssl rand -hex 32` | different value | never reuse local one |
| `JWT_ACCESS_TOKEN_MINUTES` | `60` | `60` | optional |
| `DB_POOL_SIZE` | `1` | `1` | new setting from step 2 |
| `ALLOWED_CORS_ORIGINS` | prod domain | — | harmless with same origin |
| `INITIAL_ADMIN_*` | not set on Vercel | — | only used by local seed run |

## 6. First deploy runbook

1. Land code changes on a branch; open PR → Vercel preview builds.
2. Vercel dashboard: import GitHub repo `SinghChinmayy/Go-based-exposure-and-asset-monitoring-tool`, root = repo root, framework preset = Other.
3. Add Neon from Marketplace, link to project (all environments).
4. Set `JWT_SECRET`, `DB_POOL_SIZE`.
5. From laptop, against **unpooled** URL:
   ```bash
   cd backend && DATABASE_URL="<neon unpooled>" uv run alembic upgrade head
   DATABASE_URL="<neon unpooled>" INITIAL_ADMIN_EMAIL=... INITIAL_ADMIN_PASSWORD=... uv run python -m app.scripts.seed_admin
   ```
   Optional demo data: `uv run python -m app.scripts.seed_demo`.
6. Redeploy; smoke test: `GET /health` 200, register, login, search `toyta`, admin add/restock/delete, purchase until out of stock, hard refresh on `/register` (SPA fallback works).
7. Run Playwright e2e against preview URL (follow-up: make `e2e/env.ts` accept a base URL).
8. Merge → production deploy.

## 7. Ongoing migrations

Migrations do not run in Vercel build (build has no business mutating prod, and preview builds would race). Options, pick one:
- **Manual** (start here): run `alembic upgrade head` against unpooled URL before merging a PR that adds a migration.
- **GitHub Action** (later): on push to `main`, run `alembic upgrade head` with `DATABASE_URL_UNPOOLED` secret, before Vercel promotes.

Migrations must stay backward compatible for one deploy (old function code may hit new schema briefly).

## 8. Risks and limits

- **Cold starts**: first request after idle ~1–2 s (Python import + argon2 + DB connect). Acceptable for kata.
- **Argon2 cost** on login/register runs inside the function; keep `maxDuration` ≥ 10 s.
- **Concurrency guarantees** (atomic purchase, restock) live in SQL, so they hold across many function instances.
- **No rate limiting** on `/api/auth/*` — add a Vercel Firewall rate-limit rule as cheap mitigation.
- **Logs**: JSON logs go to Vercel function logs (stdout); request IDs preserved.
- **Free-tier limits**: Neon free branch auto-suspends (adds ~0.5 s wake); Vercel Hobby is non-commercial.

## 9. Open decisions

1. One Vercel project (recommended) or two?
2. Neon (recommended) or Supabase Postgres?
3. Region: Mumbai (`bom1` + Neon `ap-south-1`) or US East?
4. Migrations: manual first, or GitHub Action from day one?
5. Seed demo data in production?
