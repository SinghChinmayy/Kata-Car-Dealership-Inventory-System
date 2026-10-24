"""enable trigram similarity for typo-tolerant search

Revision ID: 0008_trigram_search
Revises: 0007_stock_adjustments
Create Date: 2026-10-24 00:00:00.000000
"""

from alembic import op

revision = "0008_trigram_search"
down_revision = "0007_stock_adjustments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """pg_trgm ships with PostgreSQL and is trusted, so the database owner can enable it."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
