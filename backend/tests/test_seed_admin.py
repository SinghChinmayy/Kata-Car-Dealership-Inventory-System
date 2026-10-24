from sqlalchemy import text

ADMIN_EMAIL = "Owner@Example.com"
ADMIN_PASSWORD = "initial-admin-password"


def configure(monkeypatch, postgres_url: str, **overrides: str) -> None:
    """Point settings at the test database with the seed command's environment."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", overrides.get("email", ADMIN_EMAIL))
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", overrides.get("password", ADMIN_PASSWORD))
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()


def accounts(postgres_engine) -> list[dict]:
    with postgres_engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                text("SELECT email, role, password_hash FROM user_accounts")
            ).mappings()
        ]


def test_seed_admin_creates_the_initial_administrator(
    postgres_url: str, postgres_engine, monkeypatch, capsys
) -> None:
    """The seed command creates an Administrator who can sign in with the configured password."""
    configure(monkeypatch, postgres_url)
    from app.main import password_hasher
    from app.scripts.seed_admin import main

    main()

    created = accounts(postgres_engine)
    assert len(created) == 1
    assert created[0]["email"] == "owner@example.com"
    assert created[0]["role"] == "administrator"
    assert password_hasher.verify(ADMIN_PASSWORD, created[0]["password_hash"])
    assert "created" in capsys.readouterr().out


def test_seed_admin_is_safe_to_run_again(
    postgres_url: str, postgres_engine, monkeypatch, capsys
) -> None:
    """A second run leaves the existing administrator, including its password, untouched."""
    configure(monkeypatch, postgres_url)
    from app.scripts.seed_admin import main

    main()
    before = accounts(postgres_engine)
    configure(monkeypatch, postgres_url, password="a-different-password")
    main()

    assert accounts(postgres_engine) == before
    assert "already" in capsys.readouterr().out


def test_seed_admin_promotes_an_existing_standard_account(
    postgres_url: str, postgres_engine, monkeypatch, capsys
) -> None:
    """If the configured email already registered publicly, it becomes the administrator."""
    configure(monkeypatch, postgres_url)
    from fastapi.testclient import TestClient

    from app.main import create_app, password_hasher
    from app.scripts.seed_admin import main

    with TestClient(create_app()) as client:
        client.post(
            "/api/auth/register",
            json={"email": "owner@example.com", "password": "self-chosen-password"},
        )
    main()

    promoted = accounts(postgres_engine)
    assert len(promoted) == 1
    assert promoted[0]["role"] == "administrator"
    assert password_hasher.verify("self-chosen-password", promoted[0]["password_hash"])
    assert "promoted" in capsys.readouterr().out
