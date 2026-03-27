from sqlalchemy import text
from sqlalchemy.orm import Session


class PlatformService:
    def __init__(self, db: Session):
        self.db = db

    def check_ready(self) -> None:
        self.db.execute(text("SELECT 1"))

    def alert_counts(self, organization_id: int | None) -> dict[str, int]:
        if organization_id is None:
            total_alerts = (
                self.db.execute(text("SELECT COUNT(*) FROM alerts")).scalar() or 0
            )
            open_alerts = (
                self.db.execute(
                    text("SELECT COUNT(*) FROM alerts WHERE status = 'open'")
                ).scalar()
                or 0
            )
            resolved_alerts = (
                self.db.execute(
                    text("SELECT COUNT(*) FROM alerts WHERE status = 'resolved'")
                ).scalar()
                or 0
            )
        else:
            params = {"org": organization_id}
            scope_filter = "organization_id = :org"
            total_alerts = (
                self.db.execute(
                    text(f"SELECT COUNT(*) FROM alerts WHERE {scope_filter}"), params
                ).scalar()
                or 0
            )
            open_alerts = (
                self.db.execute(
                    text(
                        f"SELECT COUNT(*) FROM alerts WHERE {scope_filter} AND status = 'open'"
                    ),
                    params,
                ).scalar()
                or 0
            )
            resolved_alerts = (
                self.db.execute(
                    text(
                        f"SELECT COUNT(*) FROM alerts WHERE {scope_filter} AND status = 'resolved'"
                    ),
                    params,
                ).scalar()
                or 0
            )

        return {
            "total": int(total_alerts),
            "open": int(open_alerts),
            "resolved": int(resolved_alerts),
        }
