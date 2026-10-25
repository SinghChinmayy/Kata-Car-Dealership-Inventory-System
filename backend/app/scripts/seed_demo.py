"""Create the published demo Administrator and buyer, and reset the catalogue to samples.

Rerunning it is the demo reset: accounts are kept, and every active listing is replaced by a
fresh copy of SAMPLE_LISTINGS.
"""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.main import (
    SPEC_COLUMNS,
    SPEC_FIELDS,
    SPEC_PARAMETERS,
    RegisterRequest,
    password_hasher,
)

# The project's public Vercel Blob store (car-photos). Its photos are copies of public-domain
# or CC0 Wikimedia Commons files, which need no attribution.
PHOTOS = "https://a4djhfyric3en0ge.public.blob.vercel-storage.com/cars/"


def sample(
    make: str, model: str, category: str, price: str, quantity: int, photo: str, **specs: object
) -> dict[str, object]:
    """One sample listing as statement parameters; specs it leaves out are null."""
    return {
        "make": make,
        "model": model,
        "category": category,
        "price": Decimal(price),
        "quantity": quantity,
        "image_url": PHOTOS + photo,
        **{field: specs.get(field) for field in SPEC_FIELDS},
    }


# Eight sample cars with full spec sheets; the Mustang is sold out to show that state.
SAMPLE_LISTINGS = [
    sample(
        "Tata",
        "Nexon",
        "SUV",
        "1250000.00",
        5,
        "tata-nexon.jpg",
        year=2024,
        colour="Blue with a white roof",
        fuel_type="Petrol",
        engine_cc=1199,
        power_bhp=118,
        transmission="Manual",
        seats=5,
        mileage_kmpl=Decimal("17.4"),
        description="Compact SUV with a 1.2-litre turbo-petrol engine and five-star safety.",
    ),
    sample(
        "Mahindra",
        "XUV 3XO",
        "SUV",
        "1149000.00",
        3,
        "mahindra-xuv-3xo.jpg",
        year=2025,
        colour="White",
        fuel_type="Petrol",
        engine_cc=1197,
        power_bhp=129,
        transmission="Automatic",
        seats=5,
        mileage_kmpl=Decimal("18.2"),
        description="Sub-four-metre SUV with a panoramic sunroof and Level 2 driver assistance.",
    ),
    sample(
        "Hyundai",
        "Creta",
        "SUV",
        "1450000.00",
        4,
        "hyundai-creta.jpg",
        year=2024,
        colour="Orange",
        fuel_type="Petrol",
        engine_cc=1497,
        power_bhp=113,
        transmission="Automatic",
        seats=5,
        mileage_kmpl=Decimal("17.4"),
        description="Mid-size SUV with ventilated front seats and a panoramic sunroof.",
    ),
    sample(
        "Maruti Suzuki",
        "Swift",
        "Hatchback",
        "699000.00",
        8,
        "maruti-suzuki-swift.jpg",
        year=2024,
        colour="White",
        fuel_type="Petrol",
        engine_cc=1197,
        power_bhp=80,
        transmission="Manual",
        seats=5,
        mileage_kmpl=Decimal("24.8"),
        description="Light, nimble city hatchback with class-leading fuel economy.",
    ),
    sample(
        "Honda",
        "City",
        "Sedan",
        "1350000.00",
        2,
        "honda-city.jpg",
        year=2023,
        colour="Silver",
        fuel_type="Petrol",
        engine_cc=1498,
        power_bhp=119,
        transmission="Manual",
        seats=5,
        mileage_kmpl=Decimal("17.8"),
        description="Spacious mid-size sedan with a refined 1.5-litre i-VTEC petrol engine.",
    ),
    sample(
        "Toyota",
        "Hilux",
        "Truck",
        "3740000.00",
        1,
        "toyota-hilux.jpg",
        year=2024,
        colour="Black",
        fuel_type="Diesel",
        engine_cc=2755,
        power_bhp=201,
        transmission="Automatic",
        seats=5,
        mileage_kmpl=Decimal("10.0"),
        description="Double-cab pickup with four-wheel drive and a 2.8-litre turbo-diesel engine.",
    ),
    sample(
        "Kia",
        "Carnival",
        "Van",
        "6390000.00",
        2,
        "kia-carnival.jpg",
        year=2024,
        colour="Grey",
        fuel_type="Diesel",
        engine_cc=2151,
        power_bhp=190,
        transmission="Automatic",
        seats=7,
        mileage_kmpl=Decimal("14.9"),
        description="Premium MPV with twin power-sliding doors and lounge-style second-row seats.",
    ),
    sample(
        "Ford",
        "Mustang",
        "Coupe",
        "7500000.00",
        0,
        "ford-mustang.jpg",
        year=2024,
        colour="Grey",
        fuel_type="Petrol",
        engine_cc=4951,
        power_bhp=480,
        transmission="Manual",
        seats=4,
        mileage_kmpl=Decimal("7.0"),
        description="Two-door coupe with a naturally aspirated 5.0-litre V8 and a manual gearbox.",
    ),
]


def main() -> None:
    settings = get_settings()
    demo_accounts = [
        (settings.demo_admin_email, settings.demo_admin_password, "administrator"),
        (settings.demo_buyer_email, settings.demo_buyer_password, "standard_user"),
    ]
    with get_session_factory()() as session:
        for email, password, role in demo_accounts:
            credentials = RegisterRequest(email=email, password=password)
            existing = session.execute(
                text("SELECT role FROM user_accounts WHERE email = :email"),
                {"email": credentials.email.strip().lower()},
            ).scalar_one_or_none()
            # Rerunning is the reset: existing demo accounts keep their passwords.
            if existing == role:
                continue
            # Someone else registered this address first and controls its password, so
            # publishing it as a demo login would mislead visitors.
            if existing is not None:
                raise SystemExit(
                    f"Demo email {credentials.email.strip().lower()} already belongs to "
                    "another account; choose a different demo email."
                )
            session.execute(
                text(
                    "INSERT INTO user_accounts (id, email, password_hash, role) "
                    "VALUES (:id, :email, :password_hash, :role)"
                ),
                {
                    "id": uuid4(),
                    "email": credentials.email.strip().lower(),
                    "password_hash": password_hasher.hash(credentials.password),
                    "role": role,
                },
            )
        admin_id = session.execute(
            text("SELECT id FROM user_accounts WHERE email = :email"),
            {"email": settings.demo_admin_email.strip().lower()},
        ).scalar_one()
        # Soft delete, not DELETE: purchases keep pointing at the listings they bought.
        session.execute(
            text(
                "UPDATE vehicle_listings SET deleted_at = CURRENT_TIMESTAMP, deleted_by = :admin "
                "WHERE deleted_at IS NULL"
            ),
            {"admin": admin_id},
        )
        for listing in SAMPLE_LISTINGS:
            session.execute(
                text(
                    "INSERT INTO vehicle_listings "
                    f"(id, make, model, category, price, quantity, image_url, {SPEC_COLUMNS}) "
                    "VALUES (:id, :make, :model, :category, :price, :quantity, :image_url, "
                    f"{SPEC_PARAMETERS})"
                ),
                {"id": uuid4(), **listing},
            )
        session.commit()
    print(f"Demo accounts ready; catalogue reset to {len(SAMPLE_LISTINGS)} sample vehicles.")


if __name__ == "__main__":
    main()
