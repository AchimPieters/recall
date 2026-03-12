from pathlib import Path

from sqlalchemy import create_engine, text

from backend.app.db.migrate import apply_sql_migrations


def test_apply_sql_migrations_orders_and_is_idempotent(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    (migrations_dir / "0001_create_widgets.sql").write_text(
        """
        CREATE TABLE widgets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )
    (migrations_dir / "0002_seed_widgets.sql").write_text(
        "INSERT INTO widgets (id, name) VALUES (1, 'starter');",
        encoding="utf-8",
    )

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")

    first_run = apply_sql_migrations(engine, migrations_dir)
    second_run = apply_sql_migrations(engine, migrations_dir)

    assert first_run == ["0001_create_widgets.sql", "0002_seed_widgets.sql"]
    assert second_run == []

    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM widgets")).scalar_one()
        applied = conn.execute(
            text("SELECT COUNT(*) FROM schema_migrations")
        ).scalar_one()

    assert count == 1
    assert applied == 2
