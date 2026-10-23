import logging
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_database_readiness(postgres_url: str, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["X-Request-ID"])


def test_invalid_request_id_is_replaced_with_a_uuid(postgres_url: str, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"X-Request-ID": "not-a-uuid"})

    assert response.status_code == 200
    UUID(response.headers["X-Request-ID"])


def test_request_log_never_contains_bearer_token_or_password(
    postgres_url: str, monkeypatch, caplog
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    secret_token = "extremely-secret-token"
    secret_password = "correct-horse-battery-staple"
    with caplog.at_level(logging.INFO, logger="app"):
        with TestClient(create_app()) as client:
            response = client.post(
                "/health",
                headers={"Authorization": f"Bearer {secret_token}"},
                json={"password": secret_password},
            )

    assert response.status_code == 405
    output = caplog.text
    assert secret_token not in output
    assert secret_password not in output
