import base64
import json
import time
from uuid import UUID, uuid4

import jwt
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


def test_registration_returns_conflict_for_a_duplicate_normalized_email(
    postgres_url: str, monkeypatch
) -> None:
    """Public registration reports a normalized-email conflict without exposing credentials."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    with TestClient(create_app()) as client:
        first_response = client.post(
            "/api/auth/register",
            json={"email": "buyer@example.com", "password": "valid-password"},
        )
        duplicate_response = client.post(
            "/api/auth/register",
            json={"email": " BUYER@example.com ", "password": "valid-password"},
        )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    error = duplicate_response.json()["error"]
    assert error["code"] == "duplicate_email"
    assert "password_hash" not in duplicate_response.text
    UUID(error["request_id"])


def test_valid_credentials_issue_an_access_token(postgres_url: str, monkeypatch) -> None:
    """Login grants a one-hour bearer token to an existing Standard User."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "buyer@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        login_response = client.post("/api/auth/login", json=credentials)

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    token_response = login_response.json()
    assert set(token_response) == {"access_token", "token_type"}
    assert token_response["token_type"] == "bearer"

    token_parts = token_response["access_token"].split(".")
    assert len(token_parts) == 3
    payload_segment = token_parts[1] + "=" * (-len(token_parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload_segment))
    assert claims["sub"] == registration_response.json()["id"]
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert 3590 <= claims["exp"] - claims["iat"] <= 3610


def test_invalid_login_credentials_return_an_indistinguishable_401(
    postgres_url: str, monkeypatch
) -> None:
    """Unknown accounts and wrong passwords do not disclose which credential failed."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        registration_response = client.post(
            "/api/auth/register",
            json={"email": "buyer@example.com", "password": "valid-password"},
        )
        unknown_email_response = client.post(
            "/api/auth/login",
            json={"email": "unknown@example.com", "password": "valid-password"},
        )
        wrong_password_response = client.post(
            "/api/auth/login",
            json={"email": "buyer@example.com", "password": "incorrect-password"},
        )

    assert registration_response.status_code == 201
    errors = [unknown_email_response.json()["error"], wrong_password_response.json()["error"]]
    assert [unknown_email_response.status_code, wrong_password_response.status_code] == [401, 401]
    assert [error["code"] for error in errors] == ["invalid_credentials", "invalid_credentials"]
    assert errors[0]["message"] == errors[1]["message"]
    for error in errors:
        UUID(error["request_id"])


def test_current_user_endpoint_returns_safe_account_for_a_valid_bearer_token(
    postgres_url: str, monkeypatch
) -> None:
    """Protected identity lookup reads the current account represented by a valid token."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "buyer@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        login_response = client.post("/api/auth/login", json=credentials)
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        )

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": registration_response.json()["id"],
        "email": "buyer@example.com",
        "role": "standard_user",
    }


def test_invalid_or_missing_bearer_tokens_return_unauthorized(
    postgres_url: str, monkeypatch
) -> None:
    """Every unusable bearer token fails with the same authorization boundary response."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "buyer@example.com", "password": "valid-password"}

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        now = int(time.time())
        valid_claims = {"sub": registration_response.json()["id"], "iat": now, "exp": now + 3600}
        tokens = [
            None,
            "not.a.jwt",
            jwt.encode(
                {**valid_claims, "exp": now - 1}, get_settings().jwt_secret, algorithm="HS256"
            ),
            jwt.encode(valid_claims, "a-different-high-entropy-secret", algorithm="HS256"),
            jwt.encode(
                {**valid_claims, "sub": str(uuid4())},
                get_settings().jwt_secret,
                algorithm="HS256",
            ),
        ]
        responses = [
            client.get(
                "/api/auth/me",
                headers={} if token is None else {"Authorization": f"Bearer {token}"},
            )
            for token in tokens
        ]

    assert registration_response.status_code == 201
    assert [response.status_code for response in responses] == [401] * len(responses)
    for response in responses:
        error = response.json()["error"]
        assert error["code"] == "unauthorized"
        UUID(error["request_id"])


def test_administrator_dependency_forbids_standard_users_and_allows_administrators(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Administrator authorization is decided from the account role loaded for each request."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "buyer@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        login_response = client.post("/api/auth/login", json=credentials)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        standard_response = client.get("/api/auth/admin-check", headers=headers)
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": registration_response.json()["id"]},
            )
        administrator_response = client.get("/api/auth/admin-check", headers=headers)

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    assert standard_response.status_code == 403
    standard_error = standard_response.json()["error"]
    assert standard_error["code"] == "forbidden"
    UUID(standard_error["request_id"])
    assert administrator_response.status_code == 200
    assert administrator_response.json() == {"status": "ok"}


def test_demoted_administrator_loses_access_with_the_same_token(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Roles are read per request, so a demotion takes effect before the token expires."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "admin@example.com", "password": "valid-password"}
    listing = {"make": "Tata", "model": "Nexon", "category": "SUV", "price": "1.00", "quantity": 1}

    with TestClient(create_app()) as client:
        account_id = client.post("/api/auth/register", json=credentials).json()["id"]
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": account_id},
            )
        token = client.post("/api/auth/login", json=credentials).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        before = client.post("/api/vehicles", headers=headers, json=listing)
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'standard_user' WHERE id = :id"),
                {"id": account_id},
            )
        after = client.post("/api/vehicles", headers=headers, json=listing)

    assert before.status_code == 201
    assert after.status_code == 403
    assert after.json()["error"]["code"] == "forbidden"


def test_registration_ignores_a_requested_role(postgres_url: str, monkeypatch) -> None:
    """Public registration can never self-assign administrator authority (ADR 0004)."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "climber@example.com",
                "password": "valid-password",
                "role": "administrator",
            },
        )

    assert response.status_code == 201
    assert response.json()["role"] == "standard_user"


def test_api_exposes_no_test_only_admin_check_route(postgres_url: str, monkeypatch) -> None:
    """Authorization is exercised through real admin routes, not a probe shipped in the API."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    with TestClient(create_app()) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/api/auth/admin-check" not in paths
