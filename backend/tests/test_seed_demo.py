from sqlalchemy import text

DEMO_ADMIN_EMAIL = "Demo.Admin@Example.com"
DEMO_ADMIN_PASSWORD = "demo-admin-password"
DEMO_BUYER_EMAIL = "demo.buyer@example.com"
DEMO_BUYER_PASSWORD = "demo-buyer-password"


def configure(monkeypatch, postgres_url: str, **overrides: str) -> None:
    """Point settings at the test database with the demo seed's environment."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("DEMO_ADMIN_EMAIL", overrides.get("admin_email", DEMO_ADMIN_EMAIL))
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", overrides.get("admin_password", DEMO_ADMIN_PASSWORD))
    monkeypatch.setenv("DEMO_BUYER_EMAIL", overrides.get("buyer_email", DEMO_BUYER_EMAIL))
    monkeypatch.setenv("DEMO_BUYER_PASSWORD", overrides.get("buyer_password", DEMO_BUYER_PASSWORD))
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()


def accounts(postgres_engine) -> dict[str, dict]:
    with postgres_engine.connect() as connection:
        return {
            row["email"]: dict(row)
            for row in connection.execute(
                text("SELECT email, role, password_hash FROM user_accounts")
            ).mappings()
        }


def test_seed_demo_creates_a_demo_administrator_and_buyer(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Visitors sign in with the published demo logins, one per role."""
    configure(monkeypatch, postgres_url)
    from app.main import password_hasher
    from app.scripts.seed_demo import main

    main()

    created = accounts(postgres_engine)
    assert set(created) == {"demo.admin@example.com", "demo.buyer@example.com"}
    admin = created["demo.admin@example.com"]
    buyer = created["demo.buyer@example.com"]
    assert admin["role"] == "administrator"
    assert buyer["role"] == "standard_user"
    assert password_hasher.verify(DEMO_ADMIN_PASSWORD, admin["password_hash"])
    assert password_hasher.verify(DEMO_BUYER_PASSWORD, buyer["password_hash"])


def test_seed_demo_is_safe_to_run_again(postgres_url: str, postgres_engine, monkeypatch) -> None:
    """Rerunning it (the reset) keeps the demo accounts and their passwords as they are."""
    configure(monkeypatch, postgres_url)
    from app.scripts.seed_demo import main

    main()
    before = accounts(postgres_engine)
    configure(monkeypatch, postgres_url, admin_password="another-admin-password")
    main()

    assert accounts(postgres_engine) == before
