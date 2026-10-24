"""Create the initial Administrator from INITIAL_ADMIN_* settings (ADR 0004)."""

from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.main import RegisterRequest, password_hasher


def main() -> None:
    settings = get_settings()
    # The initial administrator meets the same email and password rules as public registration.
    try:
        credentials = RegisterRequest(
            email=settings.initial_admin_email, password=settings.initial_admin_password
        )
    except ValidationError as exc:
        setting = {"email": "INITIAL_ADMIN_EMAIL", "password": "INITIAL_ADMIN_PASSWORD"}
        invalid = sorted({setting[str(error["loc"][0])] for error in exc.errors()})
        raise SystemExit(
            f"Set a valid {' and '.join(invalid)} (email address; password of 12-128 characters)."
        ) from exc
    email = credentials.email.strip().lower()
    with get_session_factory()() as session:
        existing = session.execute(
            text("SELECT role FROM user_accounts WHERE email = :email"), {"email": email}
        ).scalar_one_or_none()
        # Idempotent: an existing account is never re-created or given a new password.
        if existing == "administrator":
            print(f"Administrator {email} already exists; nothing changed.")
            return
        if existing is not None:
            session.execute(
                text("UPDATE user_accounts SET role = 'administrator' WHERE email = :email"),
                {"email": email},
            )
            session.commit()
            print(f"Existing account {email} promoted to administrator; password unchanged.")
            return
        session.execute(
            text(
                "INSERT INTO user_accounts (id, email, password_hash, role) "
                "VALUES (:id, :email, :password_hash, 'administrator')"
            ),
            {
                "id": uuid4(),
                "email": email,
                "password_hash": password_hasher.hash(credentials.password),
            },
        )
        session.commit()
    print(f"Initial administrator {email} created.")


if __name__ == "__main__":
    main()
