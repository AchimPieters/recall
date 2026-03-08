"""baseline schema

Revision ID: 20260308_0001
Revises:
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260308_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline marker migration; legacy SQL migrations remain in recall/db/migrations.
    op.create_table(
        "alembic_baseline_marker",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alembic_baseline_marker")
