import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"make": "   "}, "make"),
        ({"model": "   "}, "model"),
        ({"make": "m" * 101}, "make"),
        ({"model": "m" * 101}, "model"),
        ({"category": "Wagon"}, "category"),
        ({"price": "0.00"}, "price"),
        ({"price": "1250000.001"}, "price"),
        ({"quantity": -1}, "quantity"),
    ],
)
def test_vehicle_creation_validates_catalogue_fields(
    postgres_url: str, postgres_engine, monkeypatch, changes: dict[str, object], field: str
) -> None:
    """Creation rejects invalid catalogue data with a safe field-level 422 response."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "inventory@example.com", "password": "valid-password"}

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": registration_response.json()["id"]},
            )
        login_response = client.post("/api/auth/login", json=credentials)
        payload: dict[str, object] = {
            "make": "Tata",
            "model": "Nexon",
            "category": "SUV",
            "price": "1250000.00",
            "quantity": 3,
        }
        payload.update(changes)
        response = client.post(
            "/api/vehicles",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
            json=payload,
        )

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["fields"][field]
    UUID(error["request_id"])


def test_authenticated_user_lists_active_vehicle_listings_by_newest_first(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """The protected catalogue returns a stable paginated active-listing envelope."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "inventory@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": registration_response.json()["id"]},
            )
        login_response = client.post("/api/auth/login", json=credentials)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        for make in ("First", "Second", "Third"):
            create_response = client.post(
                "/api/vehicles",
                headers=headers,
                json={
                    "make": make,
                    "model": "Model",
                    "category": "SUV",
                    "price": "1250000.00",
                    "quantity": 3,
                },
            )
            assert create_response.status_code == 201
        response = client.get("/api/vehicles", headers=headers)

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert [listing["make"] for listing in payload["items"]] == ["Third", "Second", "First"]


def test_authenticated_user_reads_backend_owned_vehicle_categories(
    postgres_url: str, monkeypatch
) -> None:
    """The category vocabulary comes from the protected API, not duplicated client state."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "reader@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registration_response = client.post("/api/auth/register", json=credentials)
        login_response = client.post("/api/auth/login", json=credentials)
        response = client.get(
            "/api/vehicles/categories",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        )

    assert registration_response.status_code == 201
    assert login_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {
        "items": ["Sedan", "SUV", "Hatchback", "Truck", "Coupe", "Convertible", "Van"]
    }


def test_authenticated_user_searches_vehicle_listings_with_and_semantics(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Every supplied search filter narrows the protected active listing result."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "inventory@example.com", "password": "valid-password"}
    listings = [
        ("Tata", "Nexon", "SUV", "1250000.00"),
        ("Tata", "Punch", "SUV", "700000.00"),
        ("Mahindra", "XUV700", "SUV", "2500000.00"),
    ]

    with TestClient(create_app()) as client:
        registered = client.post("/api/auth/register", json=credentials)
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": registered.json()["id"]},
            )
        logged_in = client.post("/api/auth/login", json=credentials)
        headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
        for make, model, category, price in listings:
            created = client.post(
                "/api/vehicles",
                headers=headers,
                json={
                    "make": make,
                    "model": model,
                    "category": category,
                    "price": price,
                    "quantity": 1,
                },
            )
            assert created.status_code == 201
        response = client.get(
            "/api/vehicles/search",
            headers=headers,
            params={"make": "ta", "model": "nex", "category": "SUV", "min_price": "1000000.00"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [listing["model"] for listing in payload["items"]] == ["Nexon"]


def test_vehicle_search_allows_standard_users_and_rejects_missing_tokens(
    postgres_url: str, monkeypatch
) -> None:
    """Search is protected like listing: any account may search, anonymous callers may not."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "buyer@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        client.post("/api/auth/register", json=credentials)
        logged_in = client.post("/api/auth/login", json=credentials)
        headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
        standard_response = client.get("/api/vehicles/search", headers=headers)
        anonymous_response = client.get("/api/vehicles/search")

    assert standard_response.status_code == 200
    assert standard_response.json()["total"] == 0
    assert anonymous_response.status_code == 401
    assert anonymous_response.json()["error"]["code"] == "unauthorized"


def search_as_administrator(
    postgres_url: str,
    postgres_engine,
    monkeypatch,
    listings: list[tuple[str, str, str, str]],
    params: dict[str, str],
):
    """Seed listings through the API as an administrator, then run one search."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    credentials = {"email": "inventory@example.com", "password": "valid-password"}

    with TestClient(create_app()) as client:
        registered = client.post("/api/auth/register", json=credentials)
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": registered.json()["id"]},
            )
        logged_in = client.post("/api/auth/login", json=credentials)
        headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
        for make, model, category, price in listings:
            created = client.post(
                "/api/vehicles",
                headers=headers,
                json={
                    "make": make,
                    "model": model,
                    "category": category,
                    "price": price,
                    "quantity": 1,
                },
            )
            assert created.status_code == 201
        return client.get("/api/vehicles/search", headers=headers, params=params)


def test_vehicle_search_price_range_includes_both_bounds(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A listing priced exactly at min_price or max_price is inside the range."""
    response = search_as_administrator(
        postgres_url,
        postgres_engine,
        monkeypatch,
        [
            ("Tata", "Punch", "SUV", "700000.00"),
            ("Tata", "Nexon", "SUV", "1250000.00"),
            ("Mahindra", "XUV700", "SUV", "2500000.00"),
        ],
        {"min_price": "700000.00", "max_price": "1250000.00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [listing["model"] for listing in payload["items"]] == ["Nexon", "Punch"]


def test_vehicle_search_rejects_min_price_above_max_price(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """An inverted price range is a validation error, not an empty result."""
    response = search_as_administrator(
        postgres_url,
        postgres_engine,
        monkeypatch,
        [],
        {"min_price": "1250000.00", "max_price": "700000.00"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["fields"] == {"min_price": "Must be less than or equal to max_price."}
    UUID(error["request_id"])


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"category": "Bus"}, "category"),
        ({"min_price": "-1.00"}, "min_price"),
        ({"max_price": "100.123"}, "max_price"),
        ({"min_price": "cheap"}, "min_price"),
    ],
)
def test_vehicle_search_rejects_invalid_filter_values(
    postgres_url: str, postgres_engine, monkeypatch, params: dict[str, str], field: str
) -> None:
    """Out-of-vocabulary categories and malformed prices return a field-level 422."""
    response = search_as_administrator(postgres_url, postgres_engine, monkeypatch, [], params)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert list(error["fields"]) == [field]


def test_vehicle_search_trims_text_filters_and_ignores_blank_ones(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Surrounding spaces are not part of a term, and a whitespace-only term is no filter."""
    response = search_as_administrator(
        postgres_url,
        postgres_engine,
        monkeypatch,
        [
            ("Tata", "Nexon", "SUV", "1250000.00"),
            ("Mahindra", "XUV700", "SUV", "2500000.00"),
        ],
        {"make": "  tata  ", "model": "   "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [listing["model"] for listing in payload["items"]] == ["Nexon"]


@pytest.mark.parametrize("term", ["%", "_"])
def test_vehicle_search_matches_wildcard_characters_literally(
    postgres_url: str, postgres_engine, monkeypatch, term: str
) -> None:
    """LIKE wildcards in a search term are ordinary characters, not match-anything patterns."""
    response = search_as_administrator(
        postgres_url,
        postgres_engine,
        monkeypatch,
        [
            ("Tata", "Nexon", "SUV", "1250000.00"),
            ("Tata", "Punch_EV", "SUV", "1100000.00"),
            ("Tata", "Altroz%", "Hatchback", "700000.00"),
        ],
        {"model": term},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert term in payload["items"][0]["model"]


NEXON = {"make": "Tata", "model": "Nexon", "category": "SUV", "price": "1250000.00"}


def use_test_database(postgres_url: str, monkeypatch) -> None:
    """Point the application at the disposable test database."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()


def login_headers(
    client: TestClient, postgres_engine, email: str, *, administrator: bool
) -> dict[str, str]:
    """Register an account, optionally promote it, and return its bearer header."""
    credentials = {"email": email, "password": "valid-password"}
    registered = client.post("/api/auth/register", json=credentials)
    if administrator:
        with postgres_engine.begin() as connection:
            connection.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE id = :id"),
                {"id": registered.json()["id"]},
            )
    logged_in = client.post("/api/auth/login", json=credentials)
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


def test_administrator_replaces_vehicle_listing_catalogue_fields(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A full update changes catalogue fields only; stock and creation time stay put."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 3})
        response = client.put(
            f"/api/vehicles/{created.json()['id']}",
            headers=headers,
            json={"make": "  Tata ", "model": "Nexon EV", "category": "SUV", "price": "1499999.50"},
        )

    assert response.status_code == 200
    original = created.json()
    updated = response.json()
    assert updated["id"] == original["id"]
    assert updated["make"] == "Tata"
    assert updated["model"] == "Nexon EV"
    assert updated["category"] == "SUV"
    assert updated["price"] == "1499999.50"
    assert updated["quantity"] == 3
    assert updated["created_at"] == original["created_at"]
    assert datetime.fromisoformat(updated["updated_at"]) > datetime.fromisoformat(
        original["updated_at"]
    )


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"make": "   "}, "make"),
        ({"model": "x" * 101}, "model"),
        ({"category": "Bus"}, "category"),
        ({"price": "0"}, "price"),
        ({"price": "10.999"}, "price"),
        ({"make": None}, "make"),
    ],
)
def test_vehicle_update_validates_catalogue_fields(
    postgres_url: str, postgres_engine, monkeypatch, changes: dict[str, object], field: str
) -> None:
    """Update applies the same catalogue rules as creation, with every field required."""
    use_test_database(postgres_url, monkeypatch)
    payload = {**NEXON, **changes}
    payload = {key: value for key, value in payload.items() if value is not None}

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 1})
        response = client.put(
            f"/api/vehicles/{created.json()['id']}", headers=headers, json=payload
        )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert list(error["fields"]) == [field]


def test_vehicle_update_requires_an_administrator(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Standard users are forbidden and anonymous callers unauthorized."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        admin = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        buyer = login_headers(client, postgres_engine, "buyer@example.com", administrator=False)
        created = client.post("/api/vehicles", headers=admin, json={**NEXON, "quantity": 1})
        path = f"/api/vehicles/{created.json()['id']}"
        standard_response = client.put(path, headers=buyer, json=NEXON)
        anonymous_response = client.put(path, json=NEXON)

    assert standard_response.status_code == 403
    assert standard_response.json()["error"]["code"] == "forbidden"
    assert anonymous_response.status_code == 401
    assert anonymous_response.json()["error"]["code"] == "unauthorized"


def test_vehicle_update_returns_not_found_for_unknown_listing(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A well-formed id with no listing behind it is a 404, not a server error."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        response = client.put(
            "/api/vehicles/00000000-0000-4000-8000-000000000000", headers=headers, json=NEXON
        )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    UUID(error["request_id"])


@pytest.mark.parametrize("extra", [{"quantity": 99}, {"colour": "Red"}, {"id": "ignored"}])
def test_vehicle_update_rejects_fields_outside_the_catalogue(
    postgres_url: str, postgres_engine, monkeypatch, extra: dict[str, object]
) -> None:
    """Stock and unknown keys cannot ride along on an update; quantity stays unchanged."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 3})
        response = client.put(
            f"/api/vehicles/{created.json()['id']}", headers=headers, json={**NEXON, **extra}
        )
        listed = client.get("/api/vehicles", headers=headers)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert list(error["fields"]) == list(extra)
    assert listed.json()["items"][0]["quantity"] == 3


def test_vehicle_update_rejects_a_malformed_listing_id(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A path id that is not a UUID is invalid input, reported under its bare field name."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        response = client.put("/api/vehicles/not-a-uuid", headers=headers, json=NEXON)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert list(error["fields"]) == ["listing_id"]


def test_administrator_soft_deletes_a_vehicle_listing(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Deletion retires the listing but keeps its stock and who deleted it, and when."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        admin_id = client.get("/api/auth/me", headers=headers).json()["id"]
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 3})
        response = client.delete(f"/api/vehicles/{created.json()['id']}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    with postgres_engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT quantity, deleted_at, deleted_by FROM vehicle_listings WHERE id = :id"
                ),
                {"id": created.json()["id"]},
            )
            .mappings()
            .one()
        )
    assert row["quantity"] == 3
    assert row["deleted_at"] is not None
    assert str(row["deleted_by"]) == admin_id


def test_vehicle_delete_requires_an_administrator_and_a_valid_id(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Standard users are forbidden, anonymous callers unauthorized, bad ids invalid."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        admin = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        buyer = login_headers(client, postgres_engine, "buyer@example.com", administrator=False)
        created = client.post("/api/vehicles", headers=admin, json={**NEXON, "quantity": 1})
        path = f"/api/vehicles/{created.json()['id']}"
        standard_response = client.delete(path, headers=buyer)
        anonymous_response = client.delete(path)
        malformed_response = client.delete("/api/vehicles/not-a-uuid", headers=admin)
        listed = client.get("/api/vehicles", headers=admin)

    assert standard_response.status_code == 403
    assert anonymous_response.status_code == 401
    assert malformed_response.status_code == 422
    assert list(malformed_response.json()["error"]["fields"]) == ["listing_id"]
    assert listed.json()["total"] == 1


def test_deletion_audit_columns_are_set_together(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """The database refuses a deletion time without the deleting administrator."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 1})

    with pytest.raises(IntegrityError), postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE vehicle_listings SET deleted_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": created.json()["id"]},
        )


def test_deleted_listings_are_hidden_from_list_and_search(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Normal catalogue reads only ever show active listings."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        retired = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        client.post(
            "/api/vehicles", headers=headers, json={**NEXON, "model": "Harrier", "quantity": 1}
        )
        client.delete(f"/api/vehicles/{retired.json()['id']}", headers=headers)
        listed = client.get("/api/vehicles", headers=headers)
        searched = client.get("/api/vehicles/search", headers=headers, params={"make": "tata"})

    for response in (listed, searched):
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert [listing["model"] for listing in response.json()["items"]] == ["Harrier"]


def test_vehicle_delete_returns_not_found_for_unknown_listing(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Deleting an id with no listing behind it is a 404, not a server error."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        response = client.delete(
            "/api/vehicles/00000000-0000-4000-8000-000000000000", headers=headers
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_deleting_a_deleted_listing_returns_not_found_and_keeps_the_original_audit(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A retired listing is not active, so a second delete neither succeeds nor rewrites history."""
    use_test_database(postgres_url, monkeypatch)
    audit_query = text("SELECT deleted_at, deleted_by FROM vehicle_listings WHERE id = :id")

    with TestClient(create_app()) as client:
        first = login_headers(client, postgres_engine, "first@example.com", administrator=True)
        second = login_headers(client, postgres_engine, "second@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=first, json={**NEXON, "quantity": 1})
        path = f"/api/vehicles/{created.json()['id']}"
        client.delete(path, headers=first)
        with postgres_engine.connect() as connection:
            original = connection.execute(audit_query, {"id": created.json()["id"]}).one()
        response = client.delete(path, headers=second)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    with postgres_engine.connect() as connection:
        assert connection.execute(audit_query, {"id": created.json()["id"]}).one() == original


def test_updating_a_deleted_listing_returns_not_found(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Retired listings cannot be edited back into a different shape."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 1})
        path = f"/api/vehicles/{created.json()['id']}"
        client.delete(path, headers=headers)
        response = client.put(path, headers=headers, json={**NEXON, "model": "Nexon EV"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    with postgres_engine.connect() as connection:
        model = connection.execute(
            text("SELECT model FROM vehicle_listings WHERE id = :id"),
            {"id": created.json()["id"]},
        ).scalar_one()
    assert model == "Nexon"


def test_purchase_takes_one_unit_and_returns_the_updated_listing(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A purchase decrements stock by exactly one without counting as a catalogue edit."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        admin = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        buyer = login_headers(client, postgres_engine, "buyer@example.com", administrator=False)
        created = client.post("/api/vehicles", headers=admin, json={**NEXON, "quantity": 3})
        response = client.post(f"/api/vehicles/{created.json()['id']}/purchase", headers=buyer)

    assert response.status_code == 200
    original = created.json()
    purchased = response.json()
    assert purchased["id"] == original["id"]
    assert purchased["quantity"] == 2
    assert purchased["updated_at"] == original["updated_at"]


def test_purchase_is_open_to_any_authenticated_account(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Administrators may buy like anyone else; anonymous callers cannot."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        admin = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=admin, json={**NEXON, "quantity": 3})
        path = f"/api/vehicles/{created.json()['id']}/purchase"
        anonymous_response = client.post(path)
        admin_response = client.post(path, headers=admin)

    assert anonymous_response.status_code == 401
    assert anonymous_response.json()["error"]["code"] == "unauthorized"
    assert admin_response.status_code == 200
    assert admin_response.json()["quantity"] == 2


def test_purchase_records_who_bought_what_at_which_price(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Each purchase stores catalogue snapshots that later admin edits never change."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        admin = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        buyer = login_headers(client, postgres_engine, "buyer@example.com", administrator=False)
        buyer_id = client.get("/api/auth/me", headers=buyer).json()["id"]
        created = client.post("/api/vehicles", headers=admin, json={**NEXON, "quantity": 3})
        listing_id = created.json()["id"]
        client.post(f"/api/vehicles/{listing_id}/purchase", headers=buyer)
        client.put(
            f"/api/vehicles/{listing_id}",
            headers=admin,
            json={"make": "Tata", "model": "Nexon EV", "category": "SUV", "price": "1600000.00"},
        )

    with postgres_engine.connect() as connection:
        purchases = (
            connection.execute(
                text(
                    "SELECT listing_id, purchaser_id, price, make, model, category, purchased_at "
                    "FROM purchases"
                )
            )
            .mappings()
            .all()
        )
    assert len(purchases) == 1
    purchase = purchases[0]
    assert str(purchase["listing_id"]) == listing_id
    assert str(purchase["purchaser_id"]) == buyer_id
    assert str(purchase["price"]) == "1250000.00"
    assert (purchase["make"], purchase["model"], purchase["category"]) == ("Tata", "Nexon", "SUV")
    assert purchase["purchased_at"] is not None


def test_failed_purchase_record_rolls_back_the_stock_decrement(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Stock never drops without an audit record: a failing insert undoes the decrement."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 3})
        with inserts_rejected(postgres_engine, "purchases"):
            response = client.post(
                f"/api/vehicles/{created.json()['id']}/purchase", headers=headers
            )
        listed = client.get("/api/vehicles", headers=headers)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert listed.json()["items"][0]["quantity"] == 3


def test_purchase_of_an_out_of_stock_listing_is_a_conflict(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Stock never goes negative and no purchase is recorded for an empty listing."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 0})
        response = client.post(f"/api/vehicles/{created.json()['id']}/purchase", headers=headers)
        listed = client.get("/api/vehicles", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "out_of_stock"
    assert listed.json()["items"][0]["quantity"] == 0
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM purchases")).scalar_one() == 0


def test_purchase_of_a_missing_or_deleted_listing_is_not_found(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Only active listings can be bought; a retired one keeps its remaining stock."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        listing_id = created.json()["id"]
        client.delete(f"/api/vehicles/{listing_id}", headers=headers)
        deleted_response = client.post(f"/api/vehicles/{listing_id}/purchase", headers=headers)
        missing_response = client.post(
            "/api/vehicles/00000000-0000-4000-8000-000000000000/purchase", headers=headers
        )

    for response in (deleted_response, missing_response):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    with postgres_engine.connect() as connection:
        quantity = connection.execute(
            text("SELECT quantity FROM vehicle_listings WHERE id = :id"), {"id": listing_id}
        ).scalar_one()
    assert quantity == 2


def test_concurrent_purchases_never_oversell(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Twenty simultaneous buyers race for five units: exactly five win, stock ends at zero."""
    use_test_database(postgres_url, monkeypatch)
    buyers = 20

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 5})
        path = f"/api/vehicles/{created.json()['id']}/purchase"
        start = threading.Barrier(buyers)

        def purchase(_: int) -> int:
            start.wait()
            return client.post(path, headers=headers).status_code

        with ThreadPoolExecutor(max_workers=buyers) as pool:
            statuses = list(pool.map(purchase, range(buyers)))
        listed = client.get("/api/vehicles", headers=headers)

    assert statuses.count(200) == 5
    assert statuses.count(409) == 15
    assert listed.json()["items"][0]["quantity"] == 0
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM purchases")).scalar_one() == 5


def test_administrator_restock_adds_units_and_returns_the_updated_listing(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Restock raises stock by the requested amount without counting as a catalogue edit."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        response = client.post(
            f"/api/vehicles/{created.json()['id']}/restock", headers=headers, json={"quantity": 5}
        )

    assert response.status_code == 200
    original = created.json()
    restocked = response.json()
    assert restocked["id"] == original["id"]
    assert restocked["quantity"] == 7
    assert restocked["updated_at"] == original["updated_at"]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"quantity": 0}, "quantity"),
        ({"quantity": -3}, "quantity"),
        ({"quantity": "many"}, "quantity"),
        ({}, "quantity"),
        ({"quantity": 1, "colour": "Red"}, "colour"),
    ],
)
def test_restock_validates_the_added_quantity(
    postgres_url: str, postgres_engine, monkeypatch, body: dict[str, object], field: str
) -> None:
    """Restock needs one positive whole quantity and nothing else."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        response = client.post(
            f"/api/vehicles/{created.json()['id']}/restock", headers=headers, json=body
        )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert list(error["fields"]) == [field]


def test_restock_requires_an_administrator(postgres_url: str, postgres_engine, monkeypatch) -> None:
    """Standard users are forbidden and anonymous callers unauthorized; stock is untouched."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        admin = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        buyer = login_headers(client, postgres_engine, "buyer@example.com", administrator=False)
        created = client.post("/api/vehicles", headers=admin, json={**NEXON, "quantity": 2})
        path = f"/api/vehicles/{created.json()['id']}/restock"
        standard_response = client.post(path, headers=buyer, json={"quantity": 5})
        anonymous_response = client.post(path, json={"quantity": 5})
        listed = client.get("/api/vehicles", headers=admin)

    assert standard_response.status_code == 403
    assert anonymous_response.status_code == 401
    assert listed.json()["items"][0]["quantity"] == 2


def test_restock_records_a_stock_adjustment(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Every restock leaves a durable record of which administrator added how many, when."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        admin_id = client.get("/api/auth/me", headers=headers).json()["id"]
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        listing_id = created.json()["id"]
        client.post(f"/api/vehicles/{listing_id}/restock", headers=headers, json={"quantity": 5})

    with postgres_engine.connect() as connection:
        adjustments = (
            connection.execute(
                text(
                    "SELECT listing_id, administrator_id, quantity, adjusted_at "
                    "FROM stock_adjustments"
                )
            )
            .mappings()
            .all()
        )
    assert len(adjustments) == 1
    adjustment = adjustments[0]
    assert str(adjustment["listing_id"]) == listing_id
    assert str(adjustment["administrator_id"]) == admin_id
    assert adjustment["quantity"] == 5
    assert adjustment["adjusted_at"] is not None


@contextmanager
def inserts_rejected(postgres_engine, table: str) -> Iterator[None]:
    """Temporarily make every insert into a table fail, to prove transactional rollback."""
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_insert() RETURNS trigger LANGUAGE plpgsql AS "
                "$$ BEGIN RAISE EXCEPTION 'insert rejected for test'; END $$"
            )
        )
        connection.execute(
            text(
                f"CREATE TRIGGER reject_insert BEFORE INSERT ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION reject_insert()"
            )
        )
    try:
        yield
    finally:
        with postgres_engine.begin() as connection:
            connection.execute(text(f"DROP TRIGGER reject_insert ON {table}"))
            connection.execute(text("DROP FUNCTION reject_insert()"))


def test_failed_stock_adjustment_rolls_back_the_restock(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Stock never rises without an audit record: a failing insert undoes the increment."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        with inserts_rejected(postgres_engine, "stock_adjustments"):
            response = client.post(
                f"/api/vehicles/{created.json()['id']}/restock",
                headers=headers,
                json={"quantity": 5},
            )
        listed = client.get("/api/vehicles", headers=headers)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert listed.json()["items"][0]["quantity"] == 2


def test_restock_of_a_missing_or_deleted_listing_is_not_found(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Only active listings can be restocked, and nothing is recorded otherwise."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        listing_id = created.json()["id"]
        client.delete(f"/api/vehicles/{listing_id}", headers=headers)
        deleted_response = client.post(
            f"/api/vehicles/{listing_id}/restock", headers=headers, json={"quantity": 5}
        )
        missing_response = client.post(
            "/api/vehicles/00000000-0000-4000-8000-000000000000/restock",
            headers=headers,
            json={"quantity": 5},
        )

    for response in (deleted_response, missing_response):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    with postgres_engine.connect() as connection:
        quantity = connection.execute(
            text("SELECT quantity FROM vehicle_listings WHERE id = :id"), {"id": listing_id}
        ).scalar_one()
        adjustments = connection.execute(
            text("SELECT COUNT(*) FROM stock_adjustments")
        ).scalar_one()
    assert quantity == 2
    assert adjustments == 0


@pytest.mark.parametrize("added", [2_147_483_646, 10**12])
def test_restock_beyond_the_stock_limit_is_rejected(
    postgres_url: str, postgres_engine, monkeypatch, added: int
) -> None:
    """Stock is a 32-bit count; a restock that would exceed it is invalid input, not a crash."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 2})
        response = client.post(
            f"/api/vehicles/{created.json()['id']}/restock",
            headers=headers,
            json={"quantity": added},
        )
        listed = client.get("/api/vehicles", headers=headers)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert list(error["fields"]) == ["quantity"]
    assert listed.json()["items"][0]["quantity"] == 2


def test_concurrent_restocks_and_purchases_keep_stock_consistent(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Racing restocks and purchases lose no update and leave stock matching the audit trail."""
    use_test_database(postgres_url, monkeypatch)
    pairs = 10

    with TestClient(create_app()) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        created = client.post("/api/vehicles", headers=headers, json={**NEXON, "quantity": 0})
        listing_path = f"/api/vehicles/{created.json()['id']}"
        start = threading.Barrier(pairs * 2)

        def act(index: int) -> tuple[str, int]:
            start.wait()
            if index % 2:
                restocked = client.post(
                    f"{listing_path}/restock", headers=headers, json={"quantity": 1}
                )
                return "restock", restocked.status_code
            return "purchase", client.post(f"{listing_path}/purchase", headers=headers).status_code

        with ThreadPoolExecutor(max_workers=pairs * 2) as pool:
            outcomes = list(pool.map(act, range(pairs * 2)))
        listed = client.get("/api/vehicles", headers=headers)

    assert outcomes.count(("restock", 200)) == pairs
    sold = outcomes.count(("purchase", 200))
    assert sold + outcomes.count(("purchase", 409)) == pairs
    assert listed.json()["items"][0]["quantity"] == pairs - sold
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM purchases")).scalar_one() == sold
        assert (
            connection.execute(text("SELECT COUNT(*) FROM stock_adjustments")).scalar_one() == pairs
        )


@pytest.mark.parametrize(("quantity", "status"), [(100_000, 201), (100_001, 422), (3 * 10**9, 422)])
def test_vehicle_creation_caps_the_starting_quantity(
    postgres_url: str, postgres_engine, monkeypatch, quantity: int, status: int
) -> None:
    """A new listing starts with at most 100,000 units; larger values are typos, not a crash."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "admin@example.com", administrator=True)
        response = client.post(
            "/api/vehicles", headers=headers, json={**NEXON, "quantity": quantity}
        )

    assert response.status_code == status
    if status == 422:
        assert list(response.json()["error"]["fields"]) == ["quantity"]


@pytest.mark.parametrize("path", ["/api/vehicles", "/api/vehicles/search"])
@pytest.mark.parametrize("page_number", ["10001", "999999999999999999"])
def test_listing_pages_beyond_the_limit_are_rejected(
    postgres_url: str, postgres_engine, monkeypatch, path: str, page_number: str
) -> None:
    """Page numbers stop at 10,000 so a hand-edited link cannot overflow the database offset."""
    use_test_database(postgres_url, monkeypatch)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        headers = login_headers(client, postgres_engine, "buyer@example.com", administrator=False)
        response = client.get(path, headers=headers, params={"page": page_number})

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["page"]


CATALOGUE = [
    ("Toyota", "Hilux", "Truck", "3700000.00"),
    ("Tata", "Nexon", "SUV", "1250000.00"),
    ("Honda", "City", "Sedan", "1300000.00"),
]


@pytest.mark.parametrize(
    ("q", "models"),
    [("hil", ["Hilux"]), ("TOY", ["Hilux"]), ("toyota hilux", ["Hilux"]), ("ci", ["City"])],
)
def test_search_q_matches_make_or_model(
    postgres_url: str, postgres_engine, monkeypatch, q: str, models: list[str]
) -> None:
    """One box finds a listing by any part of its make or its model."""
    response = search_as_administrator(
        postgres_url, postgres_engine, monkeypatch, CATALOGUE, {"q": q}
    )

    assert response.status_code == 200
    assert [listing["model"] for listing in response.json()["items"]] == models
