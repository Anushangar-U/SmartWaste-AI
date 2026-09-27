from datetime import datetime
from statistics import mean, median
from backend.database import connection


def summary():
    with connection() as db:
        def grouped(expression):
            # Expressions below are application constants, never request input.
            return {r[0]: r[1] for r in db.execute(f"SELECT {expression},COUNT(*) FROM complaints GROUP BY {expression}")}
        statuses = grouped("status")
        modes = grouped("processing_mode")
        priorities = grouped("COALESCE(human_priority,json_extract(decision,'$.priority'),'unknown')")
        areas = grouped("COALESCE(area,location_context,'not supplied')")
        backlog = db.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('submitted','processing','awaiting_review','processing_failed')").fetchone()[0]
        completed = db.execute("SELECT submitted_at,resolved_at FROM complaints WHERE status='resolved' AND resolved_at IS NOT NULL").fetchall()
    durations = [max(0,(datetime.fromisoformat(r[1])-datetime.fromisoformat(r[0])).total_seconds()/3600) for r in completed]
    return {"total": sum(statuses.values()), "by_status": statuses, "by_priority": priorities,
        "by_area": areas, "record_modes": modes, "review_backlog": backlog,
        "resolution_samples": len(durations),
        "average_resolution_hours": mean(durations) if len(durations)>=2 else None,
        "median_resolution_hours": median(durations) if len(durations)>=2 else None,
        "note": "Counts use stored submissions (linked duplicates remain separate). Resolution time needs at least two resolved cases; demo and live modes are explicitly counted."}
