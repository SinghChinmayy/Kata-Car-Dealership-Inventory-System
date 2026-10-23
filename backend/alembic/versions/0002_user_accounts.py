"""add user accounts

Revision ID: 0002_user_accounts
Revises: 0001_baseline
Create Date: 2026-10-24 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_user_accounts"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create accounts required by public registration."""
    op.create_table(
        "user_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove user accounts."""
    op.drop_table("user_accounts")
