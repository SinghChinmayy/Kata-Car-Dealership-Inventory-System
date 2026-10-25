from collections.abc import Generator

import pytest

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine


@pytest.fixture
def fresh_engine(postgres_url: str, monkeypatch) -> Generator[None, None, None]:
    """Build the app engine from this test's environment, and drop it afterwards."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()
    reset_engine()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()
    reset_engine()


@pytest.mark.parametrize(("configured", "expected"), [(None, 25), ("1", 1)])
def test_db_pool_size_sets_connections_kept_per_instance(
    fresh_engine: None, monkeypatch, configured, expected: int
) -> None:
    """Serverless runs many API copies at once; each must keep few connections open."""
    if configured is None:
        monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    else:
        monkeypatch.setenv("DB_POOL_SIZE", configured)

    assert get_engine().pool.size() == expected


def test_connections_never_prepare_statements(fresh_engine: None) -> None:
    """Behind a transaction pooler (Neon on Vercel) a prepared statement can land on a
    different server connection than the one that prepared it, so none are made."""
    with get_engine().connect() as connection:
        assert connection.connection.driver_connection.prepare_threshold is None
