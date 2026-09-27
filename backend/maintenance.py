"""Operator retention command. Defaults to dry-run; never runs automatically."""
import argparse
from datetime import datetime, timedelta, timezone
from backend.config import settings
from backend.database import initialize, connection


def retention(apply=False):
    if settings.retention_days <= 0:
        return {"eligible": 0, "deleted": 0, "disabled": True}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=settings.retention_days)).isoformat()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        count = db.execute("SELECT COUNT(*) FROM complaints WHERE status='resolved' AND resolved_at < ?", (cutoff,)).fetchone()[0]
        if apply:
            db.execute("DELETE FROM complaints WHERE status='resolved' AND resolved_at < ?", (cutoff,))
    return {"eligible": count, "deleted": count if apply else 0, "disabled": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete only expired resolved cases after backing up. Default is dry-run.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    initialize()
    print(retention(apply=args.apply))
