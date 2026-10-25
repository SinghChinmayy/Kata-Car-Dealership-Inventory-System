"""Create the published demo Administrator and buyer from DEMO_* settings."""

from uuid import uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.main import RegisterRequest, password_hasher


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
        session.commit()


if __name__ == "__main__":
    main()
