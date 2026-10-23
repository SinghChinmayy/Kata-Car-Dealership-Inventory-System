from uuid import UUID

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


def test_registration_rejects_passwords_outside_the_12_to_128_character_range(
    postgres_url: str, monkeypatch
) -> None:
    """Registration accepts neither shorter nor longer passwords than the policy permits."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    invalid_passwords = ["a" * 11, "b" * 129]

    with TestClient(create_app()) as client:
        for number, password in enumerate(invalid_passwords, start=1):
            response = client.post(
                "/api/auth/register",
                json={"email": f"buyer{number}@example.com", "password": password},
            )

            assert response.status_code == 422
            error = response.json()["error"]
            assert error["code"] == "validation_error"
            assert error["fields"]["password"]
            assert password not in error["fields"]["password"]
            UUID(error["request_id"])


def test_registration_rejects_malformed_email_addresses(postgres_url: str, monkeypatch) -> None:
    """Registration requires an email-shaped account identifier."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    malformed_email = "not-an-email"

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/auth/register",
            json={"email": malformed_email, "password": "valid-password"},
        )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["fields"]["email"]
    assert malformed_email not in error["fields"]["email"]
    UUID(error["request_id"])
