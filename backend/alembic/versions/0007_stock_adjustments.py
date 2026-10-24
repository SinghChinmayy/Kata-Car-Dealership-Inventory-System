"""add stock adjustments

Revision ID: 0007_stock_adjustments
Revises: 0006_purchases
Create Date: 2026-10-24 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_stock_adjustments"
down_revision = "0006_purchases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable records of administrators adding stock to listings."""
    op.create_table(
        "stock_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("administrator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "adjusted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["listing_id"], ["vehicle_listings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["administrator_id"], ["user_accounts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_stock_adjustments_positive_quantity"),
    )
    op.create_index("ix_stock_adjustments_listing_id", "stock_adjustments", ["listing_id"])


def downgrade() -> None:
    """Remove stock adjustments."""
    op.drop_index("ix_stock_adjustments_listing_id", table_name="stock_adjustments")
    op.drop_table("stock_adjustments")
