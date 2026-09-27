"""Persistence operations; no provider or HTTP dependencies."""
import hashlib
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from backend.database import connection

JSON_FIELDS = {"analysis", "retrieval", "decision", "validation"}
EDITABLE = JSON_FIELDS | {"status", "requires_human_review", "reviewer", "review_decision",
    "review_reason", "reviewed_at", "human_priority", "human_action", "assignee",
    "resolution_note", "resolved_at", "error_stage", "processing_started_at", "processing_attempts"}


class Conflict(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def decode(row):
    if row is None:
        return None
    result = dict(row)
    for field in JSON_FIELDS:
        result[field] = json.loads(result[field]) if result[field] else None
    result["requires_human_review"] = bool(result["requires_human_review"])
    return result


def create(text, location, idempotency_key=None):
    fingerprint = hashlib.sha256(json.dumps([text, location]).encode()).hexdigest()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            existing = db.execute("SELECT * FROM complaints WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                if existing["request_hash"] != fingerprint:
                    raise Conflict("Idempotency key was already used for different input.")
                return decode(existing), False
        for _ in range(5):
            identity, tracking, timestamp = str(uuid.uuid4()), "WM-" + secrets.token_hex(16), now()
            try:
                db.execute("""INSERT INTO complaints
                  (id,tracking_id,idempotency_key,request_hash,text,location_context,submitted_at,updated_at,status)
                  VALUES (?,?,?,?,?,?,?,?,?)""",
                  (identity, tracking, idempotency_key, fingerprint, text, location, timestamp, timestamp, "submitted"))
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise Conflict("Could not allocate a unique complaint identifier.")
        db.execute("INSERT INTO complaint_events (complaint_id,status,event,created_at) VALUES (?,?,?,?)",
                   (identity, "submitted", "submitted", timestamp))
        return decode(db.execute("SELECT * FROM complaints WHERE id=?", (identity,)).fetchone()), True


def get(identity):
    with connection() as db:
        return decode(db.execute("SELECT * FROM complaints WHERE id=?", (identity,)).fetchone())


def track(tracking):
    with connection() as db:
        return decode(db.execute("SELECT * FROM complaints WHERE tracking_id=?", (tracking,)).fetchone())


def events(identity):
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM complaint_events WHERE complaint_id=? ORDER BY id", (identity,))]


def list_cases(status=None, search=None, limit=100, offset=0, priority=None, review_needed=None):
    clauses, params = [], []
    if status:
        clauses.append("status=?")
        params.append(status)
    if search:
        clauses.append("(text LIKE ? OR tracking_id LIKE ? OR location_context LIKE ?)")
        params.extend(["%" + search + "%"] * 3)
    if priority:
        clauses.append("COALESCE(human_priority, json_extract(decision,'$.priority'))=?")
        params.append(priority)
    if review_needed is not None:
        clauses.append("requires_human_review=?")
        params.append(int(review_needed))
    sql = "SELECT * FROM complaints" + (" WHERE " + " AND ".join(clauses) if clauses else "")
    with connection() as db:
        return [decode(r) for r in db.execute(sql + " ORDER BY submitted_at DESC LIMIT ? OFFSET ?", [*params, limit, offset])]


def update(identity, changes, *, version=None, allowed=None, event=None, actor=None, note=None):
    if not changes or not set(changes) <= EDITABLE:
        raise ValueError("Invalid update fields")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT * FROM complaints WHERE id=?", (identity,)).fetchone()
        if old is None:
            raise KeyError(identity)
        if (version is not None and old["version"] != version) or (allowed and old["status"] not in allowed):
            raise Conflict("Case changed or this action is not allowed in its current status. Refresh the case.")
        encoded = {k: json.dumps(v, ensure_ascii=False) if k in JSON_FIELDS and v is not None else v for k,v in changes.items()}
        encoded["updated_at"] = now()
        db.execute("UPDATE complaints SET " + ",".join(f"{k}=?" for k in encoded) + ",version=version+1 WHERE id=?", [*encoded.values(), identity])
        if event:
            db.execute("INSERT INTO complaint_events (complaint_id,status,event,actor,note,created_at) VALUES (?,?,?,?,?,?)",
                       (identity, changes.get("status", old["status"]), event, actor, note, now()))
        return decode(db.execute("SELECT * FROM complaints WHERE id=?", (identity,)).fetchone())
