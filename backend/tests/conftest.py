import os
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from testcontainers.postgres import PostgresContainer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    """Start one disposable PostgreSQL instance and migrate it once per test session."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        os.environ["DATABASE_URL"] = url
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env={**os.environ, "DATABASE_URL": url},
            check=True,
        )
        yield url


@pytest.fixture(scope="session")
def postgres_engine(postgres_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(postgres_url, pool_size=25, max_overflow=5)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def truncate_database(postgres_engine: Engine) -> Generator[None, None, None]:
    """Keep test state isolated without replacing PostgreSQL with an in-memory fake."""
    with postgres_engine.begin() as connection:
        tables = (
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
                )
            )
            .scalars()
            .all()
        )
        if tables:
            quoted = ", ".join(f'"{table}"' for table in tables)
            connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    yield
