"""require unique user account emails

Revision ID: 0003_unique_user_account_email
Revises: 0002_user_accounts
Create Date: 2026-10-24 00:00:00.000000
"""

from alembic import op

revision = "0003_unique_user_account_email"
down_revision = "0002_user_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Prevent duplicate normalized account identities."""
    op.create_index("uq_user_accounts_email", "user_accounts", ["email"], unique=True)


def downgrade() -> None:
    """Permit duplicate account emails again."""
    op.drop_index("uq_user_accounts_email", table_name="user_accounts")
