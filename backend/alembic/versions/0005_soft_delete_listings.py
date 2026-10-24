"""soft delete vehicle listings

Revision ID: 0005_soft_delete_listings
Revises: 0004_vehicle_listings
Create Date: 2026-10-24 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_soft_delete_listings"
down_revision = "0004_vehicle_listings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Record when and by whom a listing was retired, keeping the row for auditing."""
    op.add_column(
        "vehicle_listings", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "vehicle_listings",
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_vehicle_listings_deleted_by_user_accounts",
        "vehicle_listings",
        "user_accounts",
        ["deleted_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_vehicle_listings_deletion_audit_complete",
        "vehicle_listings",
        "(deleted_at IS NULL) = (deleted_by IS NULL)",
    )


def downgrade() -> None:
    """Remove the deletion audit columns."""
    op.drop_constraint(
        "ck_vehicle_listings_deletion_audit_complete", "vehicle_listings", type_="check"
    )
    op.drop_constraint(
        "fk_vehicle_listings_deleted_by_user_accounts", "vehicle_listings", type_="foreignkey"
    )
    op.drop_column("vehicle_listings", "deleted_by")
    op.drop_column("vehicle_listings", "deleted_at")
