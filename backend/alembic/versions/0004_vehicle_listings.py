"""add vehicle listings

Revision ID: 0004_vehicle_listings
Revises: 0003_unique_user_account_email
Create Date: 2026-10-24 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_vehicle_listings"
down_revision = "0003_unique_user_account_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the durable catalogue table used by vehicle listings."""
    op.create_table(
        "vehicle_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("make", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("price > 0", name="ck_vehicle_listings_positive_price"),
        sa.CheckConstraint("quantity >= 0", name="ck_vehicle_listings_nonnegative_quantity"),
        sa.CheckConstraint(
            "category IN ('Sedan', 'SUV', 'Hatchback', 'Truck', 'Coupe', 'Convertible', 'Van')",
            name="ck_vehicle_listings_category",
        ),
    )


def downgrade() -> None:
    """Remove vehicle listings."""
    op.drop_table("vehicle_listings")
