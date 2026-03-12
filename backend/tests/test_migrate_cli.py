from __future__ import annotations

from backend.app.db import migrate_cli


def test_migrate_cli_dry_run_prints_message(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["migrate_cli", "--dry-run"])

    code = migrate_cli.main()
    output = capsys.readouterr().out

    assert code == 0
    assert "Dry-run is not yet implemented for SQL migrations." in output


def test_migrate_cli_reports_applied_migrations(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["migrate_cli"])
    monkeypatch.setattr(
        migrate_cli, "apply_sql_migrations", lambda _: ["0001_init.sql", "0002_add.sql"]
    )

    code = migrate_cli.main()
    output = capsys.readouterr().out

    assert code == 0
    assert "Applied migrations: 0001_init.sql, 0002_add.sql" in output


def test_migrate_cli_reports_no_pending_migrations(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["migrate_cli"])
    monkeypatch.setattr(migrate_cli, "apply_sql_migrations", lambda _: [])

    code = migrate_cli.main()
    output = capsys.readouterr().out

    assert code == 0
    assert "No pending migrations." in output
