"""Persistence for optional complaint photo evidence."""
import json
import uuid

from backend.database import connection
from backend.repositories.complaints import Conflict, now


def _decode(row):
    if row is None:
        return None
    result = dict(row)
    result["analysis"] = json.loads(result["analysis"]) if result.get("analysis") else None
    return result


def get_for_complaint(complaint_id: str):
    with connection() as db:
        return _decode(
            db.execute(
                "SELECT * FROM complaint_images WHERE complaint_id=?",
                (complaint_id,),
            ).fetchone()
        )


def create(
    complaint_id: str,
    *,
    stored_path: str,
    mime_type: str,
    byte_size: int,
    sha256: str,
    width: int,
    height: int,
):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM complaint_images WHERE complaint_id=?",
            (complaint_id,),
        ).fetchone()
        if existing:
            decoded = _decode(existing)
            if decoded["sha256"] != sha256:
                raise Conflict(
                    "The idempotency key is already associated with a different photo."
                )
            return decoded

        identity = str(uuid.uuid4())
        created_at = now()
        db.execute(
            """INSERT INTO complaint_images
               (id, complaint_id, stored_path, mime_type, byte_size, sha256,
                width, height, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                identity, complaint_id, stored_path, mime_type, byte_size,
                sha256, width, height, created_at,
            ),
        )
        return _decode(
            db.execute(
                "SELECT * FROM complaint_images WHERE complaint_id=?",
                (complaint_id,),
            ).fetchone()
        )


def set_analysis(complaint_id: str, analysis: dict, analysis_error: str | None = None):
    with connection() as db:
        db.execute(
            """UPDATE complaint_images
               SET analysis=?, analysis_error=?
               WHERE complaint_id=?""",
            (json.dumps(analysis, ensure_ascii=False), analysis_error, complaint_id),
        )
        row = db.execute(
            "SELECT * FROM complaint_images WHERE complaint_id=?",
            (complaint_id,),
        ).fetchone()
        if row is None:
            raise KeyError(complaint_id)
        return _decode(row)


def staff_metadata(record):
    if not record:
        return None
    return {
        "id": record["id"],
        "mime_type": record["mime_type"],
        "byte_size": record["byte_size"],
        "width": record["width"],
        "height": record["height"],
        "created_at": record["created_at"],
        "analysis": record.get("analysis"),
        "analysis_available": bool(
            record.get("analysis") and record["analysis"].get("analyzed")
        ),
    }
