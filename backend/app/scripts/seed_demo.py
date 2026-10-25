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

# (make, model, category, price in INR, quantity); one is sold out to show that state.
SAMPLE_LISTINGS = [
    ("Tata", "Nexon", "SUV", Decimal("1250000.00"), 5),
    ("Mahindra", "XUV700", "SUV", Decimal("1899000.00"), 3),
    ("Hyundai", "Creta", "SUV", Decimal("1450000.00"), 4),
    ("Maruti Suzuki", "Swift", "Hatchback", Decimal("699000.00"), 8),
    ("Honda", "City", "Sedan", Decimal("1350000.00"), 2),
    ("Toyota", "Hilux", "Truck", Decimal("3740000.00"), 1),
    ("Kia", "Carnival", "Van", Decimal("6390000.00"), 2),
    ("Ford", "Mustang", "Coupe", Decimal("7500000.00"), 0),
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
        for make, model, category, price, quantity in SAMPLE_LISTINGS:
            session.execute(
                text(
                    "INSERT INTO vehicle_listings (id, make, model, category, price, quantity) "
                    "VALUES (:id, :make, :model, :category, :price, :quantity)"
                ),
                {
                    "id": uuid4(),
                    "make": make,
                    "model": model,
                    "category": category,
                    "price": price,
                    "quantity": quantity,
                },
            )
        session.commit()
    print(f"Demo accounts ready; catalogue reset to {len(SAMPLE_LISTINGS)} sample vehicles.")


if __name__ == "__main__":
    main()
