from enum import Enum
from datetime import datetime, timezone
from backend.config import settings
from backend.repositories import complaints as repo
from backend.services.orchestrator import process_complaint, AgentError


class Status(str, Enum):
    submitted = "submitted"
    processing = "processing"
    awaiting_review = "awaiting_review"
    reviewed = "reviewed"
    assigned = "assigned"
    processing_failed = "processing_failed"
    resolved = "resolved"


def process(case):
    if case["status"] == Status.processing.value:
        started = datetime.fromisoformat(case["processing_started_at"])
        if (datetime.now(timezone.utc) - started).total_seconds() <= settings.processing_lease_seconds:
            raise repo.Conflict("Processing is still active.")
        case = repo.update(case["id"], {"status": Status.processing_failed.value, "error_stage": "interrupted"},
                           version=case["version"], event="interrupted")
    if case["processing_attempts"] >= settings.processing_max_attempts:
        raise repo.Conflict("Processing retry limit reached; use manual review.")
    case = repo.update(case["id"], {"status": Status.processing.value,
        "processing_started_at": repo.now(), "error_stage": None,
        "processing_attempts": case["processing_attempts"] + 1}, version=case["version"],
        allowed={Status.submitted.value, Status.processing_failed.value}, event="processing")
    try:
        def checkpoint(field, result):
            repo.update(case["id"], {field: result}, allowed={Status.processing.value})
        text = case["text"]
        if case.get("area"):
            text += "\nReporter supplied public area: " + case["area"]
        answers = case.get("clarification_answers") or {}
        if answers.get("duration"):
            text += "\nReporter supplied duration: " + answers["duration"]
        if answers.get("hazards") == "visible":
            text += "\nReporter observes potentially hazardous material."
        elif answers.get("hazards") == "none observed":
            text += "\nReporter observes no hazardous material."
        result = process_complaint(text, case["location_context"], resume=case,
            on_stage=checkpoint, request_id=case["id"]).model_dump(mode="json")
        return repo.update(case["id"], {**{k: result[k] for k in repo.JSON_FIELDS},
            "status": Status.awaiting_review.value,
            "review_urgency": result["decision"].get("review_urgency", "normal"),
            "requires_human_review": result["decision"]["requires_human_review"]}, event="analysis_completed")
    except AgentError as exc:
        return repo.update(case["id"], {"status": Status.processing_failed.value,
            "error_stage": exc.stage, "requires_human_review": True}, event="processing_failed")


def submit(text, location=None, idempotency_key=None, answers=None, area=None):
    case, created = repo.create(text, location, idempotency_key, answers, area)
    return (process(case) if created else case), created


def public_status(case):
    # Explicit allowlist: never expose complaint text, provider errors or staff notes.
    return {"tracking_id": case["tracking_id"], "status": case["status"],
        "mode": case.get("processing_mode", "unknown"),
        "submitted_at": case["submitted_at"], "updated_at": case["updated_at"],
        "clarification_questions": (case.get("decision") or {}).get("clarification_questions", []),
        "message": "Your complaint is saved. Staff can review it even when automated processing is unavailable.",
        "history": [{"status": e["status"], "at": e["created_at"]} for e in repo.events(case["id"])]}


def review(case, body, actor):
    if body.decision == "approve":
        if not case["decision"]:
            raise repo.Conflict("No AI recommendation exists; use an explicit manual override.")
        priority, action = case["decision"]["priority"], case["decision"]["recommended_action"]
    else:
        if not body.priority or not body.action:
            raise repo.Conflict("Override requires a priority and action.")
        priority, action = body.priority.value, body.action
    return repo.update(case["id"], {"status": Status.reviewed.value, "reviewer": actor,
        "review_decision": body.decision, "review_reason": body.reason,
        "reviewed_at": repo.now(), "human_priority": priority, "human_action": action,
        "requires_human_review": False}, version=body.version,
        allowed={Status.awaiting_review.value, Status.processing_failed.value},
        event="reviewed", actor=actor, note=body.reason)
