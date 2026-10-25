"""add an optional spec sheet to vehicle listings

Revision ID: 0010_listing_specs
Revises: 0009_listing_photos
Create Date: 2026-10-25 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_listing_specs"
down_revision = "0009_listing_photos"
branch_labels = None
depends_on = None

SPEC_COLUMNS = [
    sa.Column("year", sa.SmallInteger(), nullable=True),
    sa.Column("colour", sa.String(length=50), nullable=True),
    sa.Column("description", sa.String(length=1000), nullable=True),
    sa.Column("fuel_type", sa.String(length=16), nullable=True),
    sa.Column("engine_cc", sa.Integer(), nullable=True),
    sa.Column("battery_kwh", sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column("power_bhp", sa.SmallInteger(), nullable=True),
    sa.Column("transmission", sa.String(length=16), nullable=True),
    sa.Column("seats", sa.SmallInteger(), nullable=True),
    sa.Column("mileage_kmpl", sa.Numeric(precision=4, scale=1), nullable=True),
    sa.Column("range_km", sa.SmallInteger(), nullable=True),
]

# Backstops for the API's own validation: every value is optional, but never nonsense.
SPEC_CHECKS = {
    "ck_vehicle_listings_year": "year BETWEEN 1900 AND 2100",
    "ck_vehicle_listings_fuel_type": (
        "fuel_type IN ('Petrol', 'Diesel', 'Electric', 'Hybrid', 'CNG')"
    ),
    "ck_vehicle_listings_transmission": "transmission IN ('Manual', 'Automatic')",
    "ck_vehicle_listings_engine_cc": "engine_cc > 0",
    "ck_vehicle_listings_battery_kwh": "battery_kwh > 0",
    "ck_vehicle_listings_power_bhp": "power_bhp > 0",
    "ck_vehicle_listings_seats": "seats > 0",
    "ck_vehicle_listings_mileage_kmpl": "mileage_kmpl > 0",
    "ck_vehicle_listings_range_km": "range_km > 0",
}


def upgrade() -> None:
    """Nullable columns only, so the code still live while this deploys keeps working."""
    for column in SPEC_COLUMNS:
        op.add_column("vehicle_listings", column)
    for name, condition in SPEC_CHECKS.items():
        op.create_check_constraint(name, "vehicle_listings", condition)


def downgrade() -> None:
    """Remove the spec sheet."""
    for name in SPEC_CHECKS:
        op.drop_constraint(name, "vehicle_listings", type_="check")
    for column in reversed(SPEC_COLUMNS):
        op.drop_column("vehicle_listings", column.name)
