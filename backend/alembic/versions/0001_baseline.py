"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-24 00:00:00.000000
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Establish Alembic versioning before domain tables are introduced."""


def downgrade() -> None:
    """The baseline has no domain tables to remove."""
