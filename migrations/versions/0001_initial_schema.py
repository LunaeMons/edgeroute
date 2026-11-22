"""Initial schema: the cdn and probe tables.

Revision ID: 0001
Revises:
Created: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic uses these to put migrations in order.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the cdn and probe tables."""
    op.create_table(
        "cdn",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("enabled", sa.String(length=5), server_default="true", nullable=False),
        sa.Column("cost_per_gb_cents", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "probe",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("ttfb_ms", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_probe_region_observed_at", "probe", ["region", "observed_at"])


def downgrade() -> None:
    """Drop the tables, and every row in them."""
    op.drop_index("ix_probe_region_observed_at", table_name="probe")
    op.drop_table("probe")
    op.drop_table("cdn")
