"""Create the published demo Administrator and buyer, and reset the catalogue to samples.

Rerunning it is the demo reset: accounts are kept, and every active listing is replaced by a
fresh copy of SAMPLE_LISTINGS.
"""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.main import RegisterRequest, password_hasher


def commons_photo(file_path: str) -> str:
    """Wikimedia's 960px thumbnail of a Commons file, from its "x/xy/File_name.jpg" path."""
    name = file_path.rsplit("/", 1)[1]
    return f"https://thumb.wikimedia.org/wikipedia/commons/thumb/{file_path}/960px-{name}"


# (make, model, category, price in INR, quantity, photo); one is sold out to show that state.
# The photos are openly licensed Wikimedia Commons files, credited in docs/image-credits.md.
SAMPLE_LISTINGS = [
    (
        "Tata",
        "Nexon",
        "SUV",
        Decimal("1250000.00"),
        5,
        commons_photo("2/25/Tata_Nexon_Blue_Dual_Tone.jpg"),
    ),
    (
        "Mahindra",
        "XUV700",
        "SUV",
        Decimal("1899000.00"),
        3,
        commons_photo("b/ba/2021_Mahindra_XUV700_2.2_AX7_%28India%29_front_view.png"),
    ),
    (
        "Hyundai",
        "Creta",
        "SUV",
        Decimal("1450000.00"),
        4,
        commons_photo("7/7f/2021_Hyundai_Creta_SX%28O%29_CRDi_%28India%29_front_view.jpg"),
    ),
    (
        "Maruti Suzuki",
        "Swift",
        "Hatchback",
        Decimal("699000.00"),
        8,
        commons_photo("9/9a/2018_Suzuki_Swift_SZ5_Boosterjet_SHVS_1.0_Front.jpg"),
    ),
    (
        "Honda",
        "City",
        "Sedan",
        Decimal("1350000.00"),
        2,
        commons_photo("9/98/Honda_City_%28fifth_generation%29_facelift.jpg"),
    ),
    (
        "Toyota",
        "Hilux",
        "Truck",
        Decimal("3740000.00"),
        1,
        commons_photo("8/81/Toyota_HiLux_GR_Sport_1X7A7281.jpg"),
    ),
    (
        "Kia",
        "Carnival",
        "Van",
        Decimal("6390000.00"),
        2,
        commons_photo("f/f7/2021_Kia_Carnival_SXL.jpg"),
    ),
    (
        "Ford",
        "Mustang",
        "Coupe",
        Decimal("7500000.00"),
        0,
        commons_photo("5/5d/2018_Ford_Mustang_GT_5.0_Front.jpg"),
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
        for make, model, category, price, quantity, image_url in SAMPLE_LISTINGS:
            session.execute(
                text(
                    "INSERT INTO vehicle_listings "
                    "(id, make, model, category, price, quantity, image_url) "
                    "VALUES (:id, :make, :model, :category, :price, :quantity, :image_url)"
                ),
                {
                    "id": uuid4(),
                    "make": make,
                    "model": model,
                    "category": category,
                    "price": price,
                    "quantity": quantity,
                    "image_url": image_url,
                },
            )
        session.commit()
    print(f"Demo accounts ready; catalogue reset to {len(SAMPLE_LISTINGS)} sample vehicles.")


if __name__ == "__main__":
    main()
