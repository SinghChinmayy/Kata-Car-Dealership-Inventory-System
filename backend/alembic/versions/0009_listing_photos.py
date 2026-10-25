"""add an optional photo URL to vehicle listings

Revision ID: 0009_listing_photos
Revises: 0008_trigram_search
Create Date: 2026-10-25 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_listing_photos"
down_revision = "0008_trigram_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Nullable, so it is backward compatible with the code still live while it deploys."""
    op.add_column("vehicle_listings", sa.Column("image_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    """Remove listing photos."""
    op.drop_column("vehicle_listings", "image_url")
