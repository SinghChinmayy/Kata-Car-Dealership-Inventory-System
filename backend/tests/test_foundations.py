import logging
from uuid import UUID

import pytest
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


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [
        ("GET", "/api/nothing-here", 404, "not_found"),
        ("PATCH", "/api/vehicles/00000000-0000-4000-8000-000000000000", 405, "method_not_allowed"),
    ],
)
def test_routing_errors_use_the_standard_error_envelope(
    postgres_url: str, monkeypatch, method: str, path: str, status: int, code: str
) -> None:
    """Unknown paths and unsupported methods follow docs/api-error-contract.md too."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        response = client.request(method, path)

    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_unexpected_errors_keep_request_id_cors_and_traceback(
    postgres_url: str, monkeypatch, caplog
) -> None:
    """A crash still returns a traceable, browser-readable 500 and logs its stack trace."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    app = create_app()

    @app.get("/api/test-explosion")
    def explode() -> None:
        raise RuntimeError("simulated failure")

    with caplog.at_level(logging.INFO, logger="app"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/test-explosion", headers={"Origin": "http://localhost:5173"}
            )

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert response.headers.get("X-Request-ID") == error["request_id"]
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    failures = [record for record in caplog.records if record.getMessage() == "request.failed"]
    assert len(failures) == 1
    assert failures[0].levelno == logging.ERROR
    assert failures[0].exc_info is not None


def test_browsers_on_other_origins_can_read_the_request_id(postgres_url: str, monkeypatch) -> None:
    """With split hosting, the SPA can only show X-Request-ID if CORS exposes it."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    exposed = response.headers.get("access-control-expose-headers", "")
    assert "x-request-id" in exposed.lower()
