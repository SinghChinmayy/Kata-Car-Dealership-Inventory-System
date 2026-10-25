#!/usr/bin/env bash
# Run a backend command against the deployed Neon database, e.g.:
#   scripts/vercel_db.sh uv run alembic upgrade head
# Needs a linked Vercel project (vercel link). Uses Neon's direct URL, as migrations and
# seeds must not go through the pooler, and the published VITE_DEMO_* logins for DEMO_*.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$(mktemp)"
trap 'rm -f "$env_file"' EXIT

vercel env pull "$env_file" --environment production --yes --cwd "$root" >/dev/null

value() {
  grep "^$1=" "$env_file" | head -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'
}

export DATABASE_URL="$(value DATABASE_URL_UNPOOLED)"
export DEMO_ADMIN_EMAIL="$(value VITE_DEMO_ADMIN_EMAIL)"
export DEMO_ADMIN_PASSWORD="$(value VITE_DEMO_ADMIN_PASSWORD)"
export DEMO_BUYER_EMAIL="$(value VITE_DEMO_BUYER_EMAIL)"
export DEMO_BUYER_PASSWORD="$(value VITE_DEMO_BUYER_PASSWORD)"
# The real JWT_SECRET is a Vercel secret and cannot be pulled; these commands sign no tokens.
export JWT_SECRET="$(openssl rand -hex 32)"

cd "$root/backend"
"$@"
