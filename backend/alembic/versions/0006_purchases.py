"""add purchases

Revision ID: 0006_purchases
Revises: 0005_soft_delete_listings
Create Date: 2026-10-24 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_purchases"
down_revision = "0005_soft_delete_listings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable purchase records with catalogue snapshots taken at sale time."""
    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchaser_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("make", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["listing_id"], ["vehicle_listings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchaser_id"], ["user_accounts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("price > 0", name="ck_purchases_positive_price"),
        sa.CheckConstraint(
            "category IN ('Sedan', 'SUV', 'Hatchback', 'Truck', 'Coupe', 'Convertible', 'Van')",
            name="ck_purchases_category",
        ),
    )
    op.create_index("ix_purchases_purchaser_id", "purchases", ["purchaser_id"])


def downgrade() -> None:
    """Remove purchases."""
    op.drop_index("ix_purchases_purchaser_id", table_name="purchases")
    op.drop_table("purchases")
