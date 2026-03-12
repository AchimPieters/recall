from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def _make_config(db_path: Path, migrations_path: Path) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.cmd_opts = Namespace(x=[f"migrations_path={migrations_path}"])
    return config


def test_alembic_bridge_applies_sql_migrations(tmp_path: Path) -> None:
    db_path = tmp_path / "alembic.db"
    migrations_path = tmp_path / "migrations"
    migrations_path.mkdir()
    (migrations_path / "0001_init.sql").write_text(
        "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT NOT NULL);",
        encoding="utf-8",
    )
    (migrations_path / "0002_add_seed.sql").write_text(
        "INSERT INTO test_table (id, name) VALUES (1, 'seed');",
        encoding="utf-8",
    )

    config = _make_config(db_path, migrations_path)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "schema_migrations" in table_names
    assert "test_table" in table_names

    with engine.connect() as conn:
        applied = conn.execute(
            text("SELECT COUNT(*) FROM schema_migrations")
        ).scalar_one()
        seeded = conn.execute(
            text("SELECT COUNT(*) FROM test_table WHERE id = 1")
        ).scalar_one()

    assert applied == 2
    assert seeded == 1
