from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection


MIGRATION_TABLE = "schema_migrations"


def _migration_dir(default: Path | None = None) -> Path:
    if default is not None:
        return default
    return Path(__file__).resolve().parent / "migrations"


def discover_migration_files(migrations_path: Path | None = None) -> list[Path]:
    migration_dir = _migration_dir(migrations_path)
    return sorted(
        [path for path in migration_dir.glob("*.sql") if path.is_file()],
        key=lambda path: path.name,
    )


def _ensure_migration_table(conn) -> None:
    conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _applied_versions(conn) -> set[str]:
    rows = conn.execute(text(f"SELECT version FROM {MIGRATION_TABLE}"))
    return {row[0] for row in rows}


def _split_statements(sql: str) -> Iterable[str]:
    for part in sql.split(";"):
        statement = part.strip()
        if statement:
            yield statement


def apply_sql_migrations_connection(conn: Connection, migrations_path: Path | None = None) -> list[str]:
    applied: list[str] = []
    migration_files = discover_migration_files(migrations_path)

    _ensure_migration_table(conn)
    completed = _applied_versions(conn)
    for migration_file in migration_files:
        version = migration_file.name
        if version in completed:
            continue

        sql = migration_file.read_text(encoding="utf-8").strip()
        if sql:
            if conn.engine.dialect.name == "sqlite":
                raw_connection = conn.connection
                raw_connection.executescript(sql)
            else:
                for statement in _split_statements(sql):
                    conn.exec_driver_sql(statement)

        conn.execute(
            text(
                f"INSERT INTO {MIGRATION_TABLE} (version) VALUES (:version)"
            ),
            {"version": version},
        )
        applied.append(version)

    return applied


def apply_sql_migrations(engine: Engine, migrations_path: Path | None = None) -> list[str]:
    with engine.begin() as conn:
        return apply_sql_migrations_connection(conn, migrations_path=migrations_path)
