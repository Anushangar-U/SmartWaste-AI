"""Bounded suggestions only; never merge or remove citizen submissions."""
import sqlite3
from datetime import datetime, timedelta
from functools import lru_cache
from backend.config import settings
from backend.database import connection
from backend.repositories import complaints as repo


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    from retrieval.processing.embedder import DEFAULT_MODEL_NAME
    # Optional suggestions must not trigger a hidden model download.
    return SentenceTransformer(DEFAULT_MODEL_NAME, local_files_only=True)


def semantic_scores(texts):
    vectors = _model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [float(vectors[0] @ vector) for vector in vectors[1:]]


def suggestions(case, scorer=None):
    if not case.get("area"):
        return {"available": True, "suggestions": [], "reason": "No explicit area supplied; location type alone is not a shared incident location."}
    center = datetime.fromisoformat(case["submitted_at"])
    start, end = center - timedelta(days=settings.duplicate_window_days), center + timedelta(days=settings.duplicate_window_days)
    with connection() as db:
        rows = [repo.decode(r) for r in db.execute("""SELECT * FROM complaints
            WHERE id != ? AND lower(area)=lower(?) AND submitted_at BETWEEN ? AND ?
            ORDER BY submitted_at DESC LIMIT 100""", (case["id"], case["area"], start.isoformat(), end.isoformat()))]
        links = [dict(r) for r in db.execute("SELECT * FROM duplicate_links WHERE first_id=? OR second_id=?", (case["id"],case["id"]))]
    if not rows:
        return {"available": True, "suggestions": [], "confirmed_links": links}
    try:
        scores = (scorer or semantic_scores)([case["text"], *(row["text"] for row in rows)])
    except Exception:
        return {"available": False, "suggestions": [], "confirmed_links": links,
                "reason": "Local semantic model unavailable; staff may review incidents manually."}
    matches = [{"id": row["id"], "tracking_id": row["tracking_id"], "similarity": score,
        "reason": f"Same reporter-supplied area; within {settings.duplicate_window_days} days; similar complaint text."}
        for row, score in zip(rows, scores) if score >= settings.duplicate_similarity_threshold]
    return {"available": True, "suggestions": sorted(matches, key=lambda x:x["similarity"], reverse=True)[:5], "confirmed_links": links}


def confirm(identity, other, actor, reason):
    if identity == other:
        raise repo.Conflict("A complaint cannot be linked to itself.")
    first, second = sorted([identity, other])
    try:
        with connection() as db:
            db.execute("INSERT INTO duplicate_links VALUES (?,?,?,?,?)", (first,second,actor,reason,repo.now()))
    except sqlite3.IntegrityError as exc:
        raise repo.Conflict("The cases are already linked or no longer exist.") from exc
    return {"first_id": first, "second_id": second, "merged": False, "message": "Staff-confirmed link saved; both submissions retained."}
