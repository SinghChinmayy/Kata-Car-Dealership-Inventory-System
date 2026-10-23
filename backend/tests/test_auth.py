from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app


def test_registering_creates_a_standard_user_with_an_argon2_hash(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Public registration persists a safe, password-protected Standard User."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    submitted_password = "correct-horse-battery-staple"
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "  BUYER@Example.COM ",
                "password": submitted_password,
            },
        )

    assert response.status_code == 201
    user = response.json()
    assert user == {
        "id": user["id"],
        "email": "buyer@example.com",
        "role": "standard_user",
    }
    assert "password_hash" not in user

    with postgres_engine.connect() as connection:
        stored_hash = connection.execute(
            text("SELECT password_hash FROM user_accounts WHERE email = :email"),
            {"email": "buyer@example.com"},
        ).scalar_one()

    # pwdlib is intentionally imported after the response assertions so this red
    # test first proves the missing registration behavior rather than setup.
    from pwdlib import PasswordHash

    assert stored_hash.startswith("$argon2")
    assert submitted_password not in stored_hash
    assert PasswordHash.recommended().verify(submitted_password, stored_hash)
