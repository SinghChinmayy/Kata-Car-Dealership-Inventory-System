from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app


def test_administrator_can_create_a_vehicle_listing(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Administrators can add an active Vehicle Listing to the catalogue."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "inventory@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        administrator_id = registration_response.json()["id"]
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": administrator_id},
            )
        login_response = client.post("/api/auth/login", json=credentials)
        response = client.post(
            "/api/vehicles",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
            json={
                "make": "  Tata  ",
                "model": "  Nexon  ",
                "category": "SUV",
                "price": "1250000.00",
                "quantity": 3,
            },
        )

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    assert response.status_code == 201
    listing = response.json()
    UUID(listing["id"])
    assert listing["make"] == "Tata"
    assert listing["model"] == "Nexon"
    assert listing["category"] == "SUV"
    assert listing["price"] == "1250000.00"
    assert listing["quantity"] == 3
    for field in ("created_at", "updated_at"):
        timestamp = datetime.fromisoformat(listing[field].replace("Z", "+00:00"))
        assert timestamp.tzinfo == timezone.utc
