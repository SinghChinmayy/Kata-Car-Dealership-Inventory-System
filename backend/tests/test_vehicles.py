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
