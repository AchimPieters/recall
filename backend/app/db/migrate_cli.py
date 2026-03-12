from __future__ import annotations

import argparse

from backend.app.db.database import engine
from backend.app.db.migrate import apply_sql_migrations


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Recall SQL schema migrations.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print migration plan only (no schema changes).",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("Dry-run is not yet implemented for SQL migrations.")
        return 0

    applied = apply_sql_migrations(engine)
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("No pending migrations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
