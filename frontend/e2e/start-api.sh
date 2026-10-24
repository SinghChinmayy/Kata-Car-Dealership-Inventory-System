#!/usr/bin/env bash
# Playwright webServer for the API: recreate the throwaway E2E database, migrate it,
# seed the administrator, then serve. Playwright supplies DATABASE_URL and the other
# settings (see playwright.config.ts), so the developer's database is never touched.
set -euo pipefail
cd "$(dirname "$0")/../../backend"

uv run python - <<'PY'
import os

import psycopg
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
name = url.database or ""
# Guard: this drops the database, so only ever do it to one named for E2E.
if not name.endswith("_e2e"):
    raise SystemExit(f"Refusing to reset {name!r}: the E2E database name must end in _e2e.")
maintenance = url.set(drivername="postgresql", database="postgres")
with psycopg.connect(maintenance.render_as_string(hide_password=False), autocommit=True) as conn:
    conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    conn.execute(f'CREATE DATABASE "{name}"')
print(f"Recreated database {name}.")
PY

uv run alembic upgrade head
uv run python -m app.scripts.seed_admin
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
