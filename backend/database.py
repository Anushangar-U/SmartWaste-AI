"""Small SQLite boundary. Migrations are additive and never reset user data."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from backend.config import settings


@contextmanager
def connection():
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connection() as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            raise RuntimeError("Database schema is newer than this application.")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS complaints (
          id TEXT PRIMARY KEY, tracking_id TEXT NOT NULL UNIQUE,
          idempotency_key TEXT UNIQUE, request_hash TEXT NOT NULL,
          text TEXT NOT NULL, location_context TEXT,
          submitted_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0,
          analysis TEXT, retrieval TEXT, decision TEXT, validation TEXT,
          requires_human_review INTEGER NOT NULL DEFAULT 1,
          reviewer TEXT, review_decision TEXT, review_reason TEXT, reviewed_at TEXT,
          human_priority TEXT, human_action TEXT, assignee TEXT,
          resolution_note TEXT, resolved_at TEXT, error_stage TEXT,
          processing_started_at TEXT, processing_attempts INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS complaint_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          complaint_id TEXT NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
          status TEXT NOT NULL, event TEXT NOT NULL, actor TEXT,
          note TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS complaint_status_idx ON complaints(status, submitted_at);
        PRAGMA user_version=1;
        """)


if __name__ == "__main__":
    initialize()
    print("Database initialized; existing records preserved.")
