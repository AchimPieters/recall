"""Bridge existing SQL migrations into Alembic."""

from __future__ import annotations

from pathlib import Path

from alembic import context, op
from sqlalchemy.engine import Connection

from backend.app.db.migrate import apply_sql_migrations_connection

# revision identifiers, used by Alembic.
revision = "20260311_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection: Connection = op.get_bind()
    x_args = context.get_x_argument(as_dictionary=True)
    override_path = x_args.get("migrations_path")
    migrations_path = Path(override_path) if override_path else Path(__file__).resolve().parents[2] / "app" / "db" / "migrations"
    apply_sql_migrations_connection(connection, migrations_path=migrations_path)


def downgrade() -> None:
    raise RuntimeError("Downgrade is intentionally unsupported for SQL bridge migration.")
