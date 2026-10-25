import pytest
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


def test_seed_demo_refuses_an_email_registered_with_another_role(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """If a stranger registered the demo admin email first, the seed stops rather than
    publishing a login that someone else controls."""
    configure(monkeypatch, postgres_url)
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.scripts.seed_demo import main

    with TestClient(create_app()) as client:
        client.post(
            "/api/auth/register",
            json={"email": "demo.admin@example.com", "password": "squatter-password"},
        )

    with pytest.raises(SystemExit) as exited:
        main()

    assert "demo.admin@example.com" in str(exited.value)
    assert accounts(postgres_engine)["demo.admin@example.com"]["role"] == "standard_user"


def active_listings(postgres_engine) -> list[tuple]:
    with postgres_engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT make, model, category, price, quantity FROM vehicle_listings "
                    "WHERE deleted_at IS NULL ORDER BY make, model"
                )
            )
        ]


def test_seed_demo_resets_the_catalogue_to_sample_vehicles(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """A vandalised catalogue goes back to the samples; old listings and purchases are kept."""
    from uuid import uuid4

    configure(monkeypatch, postgres_url)
    from app.main import VehicleCategory
    from app.scripts.seed_demo import main

    main()
    first_samples = active_listings(postgres_engine)
    with postgres_engine.begin() as connection:
        buyer_id = connection.execute(
            text("SELECT id FROM user_accounts WHERE email = 'demo.buyer@example.com'")
        ).scalar_one()
        vandal_listing = uuid4()
        connection.execute(
            text(
                "INSERT INTO vehicle_listings (id, make, model, category, price, quantity) "
                "VALUES (:id, 'Vandal', 'Junk', 'Van', 1, 1)"
            ),
            {"id": vandal_listing},
        )
        connection.execute(
            text(
                "INSERT INTO purchases (id, listing_id, purchaser_id, price, make, model, "
                "category) VALUES (:id, :listing, :buyer, 1, 'Vandal', 'Junk', 'Van')"
            ),
            {"id": uuid4(), "listing": vandal_listing, "buyer": buyer_id},
        )
        connection.execute(text("UPDATE vehicle_listings SET quantity = 0 WHERE make != 'Vandal'"))

    main()

    assert len(first_samples) >= 6
    assert {listing[2] for listing in first_samples} <= {c.value for c in VehicleCategory}
    assert any(listing[4] == 0 for listing in first_samples), "show one sold-out card"
    assert active_listings(postgres_engine) == first_samples
    with postgres_engine.connect() as connection:
        vandal = connection.execute(
            text(
                "SELECT l.deleted_at IS NOT NULL AS deleted, a.email AS deleted_by "
                "FROM vehicle_listings l JOIN user_accounts a ON a.id = l.deleted_by "
                "WHERE l.id = :id"
            ),
            {"id": vandal_listing},
        ).one()
        purchases = connection.execute(text("SELECT count(*) FROM purchases")).scalar_one()
    assert vandal.deleted and vandal.deleted_by == "demo.admin@example.com"
    assert purchases == 1


def sample_photos(postgres_engine) -> list:
    with postgres_engine.connect() as connection:
        return (
            connection.execute(
                text("SELECT image_url FROM vehicle_listings WHERE deleted_at IS NULL")
            )
            .scalars()
            .all()
        )


def test_seed_demo_gives_every_sample_its_own_photo(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """Each sample card shows a photo of its model, served over HTTPS."""
    configure(monkeypatch, postgres_url)
    from app.scripts.seed_demo import main

    main()

    photos = sample_photos(postgres_engine)
    assert photos
    assert all(photo and photo.startswith("https://") for photo in photos)
    assert len(set(photos)) == len(photos)


def test_seed_demo_photos_come_from_the_project_blob_store(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """The demo serves its own copies from Vercel Blob, so no third-party site can break it."""
    configure(monkeypatch, postgres_url)
    from app.scripts.seed_demo import main

    main()

    store = "https://a4djhfyric3en0ge.public.blob.vercel-storage.com/cars/"
    assert all(photo.startswith(store) for photo in sample_photos(postgres_engine))


def test_seed_demo_gives_every_sample_a_full_spec_sheet(
    postgres_url: str, postgres_engine, monkeypatch
) -> None:
    """The details dialog has a full spec sheet to show for every sample car."""
    configure(monkeypatch, postgres_url)
    from app.scripts.seed_demo import main

    main()

    with postgres_engine.connect() as connection:
        samples = (
            connection.execute(
                text(
                    "SELECT year, colour, description, fuel_type, engine_cc, battery_kwh, "
                    "power_bhp, transmission, seats, mileage_kmpl, range_km "
                    "FROM vehicle_listings WHERE deleted_at IS NULL"
                )
            )
            .mappings()
            .all()
        )
    assert samples
    for sample in samples:
        required = ("year", "colour", "description", "fuel_type", "power_bhp", "transmission")
        assert all(sample[field] is not None for field in (*required, "seats"))
        assert sample["engine_cc"] or sample["battery_kwh"], "engine size or battery"
        assert sample["mileage_kmpl"] or sample["range_km"], "mileage or range"
