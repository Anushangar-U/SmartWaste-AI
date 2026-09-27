from enum import Enum
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
    case = repo.update(case["id"], {"status": Status.processing.value,
        "processing_started_at": repo.now(), "error_stage": None,
        "processing_attempts": case["processing_attempts"] + 1}, version=case["version"],
        allowed={Status.submitted.value, Status.processing_failed.value}, event="processing")
    try:
        result = process_complaint(case["text"], case["location_context"]).model_dump(mode="json")
        return repo.update(case["id"], {**{k: result[k] for k in repo.JSON_FIELDS},
            "status": Status.awaiting_review.value,
            "requires_human_review": result["decision"]["requires_human_review"]}, event="analysis_completed")
    except AgentError as exc:
        return repo.update(case["id"], {"status": Status.processing_failed.value,
            "error_stage": exc.stage, "requires_human_review": True}, event="processing_failed")


def submit(text, location=None, idempotency_key=None):
    case, created = repo.create(text, location, idempotency_key)
    return (process(case) if created else case), created


def public_status(case):
    # Explicit allowlist: never expose complaint text, provider errors or staff notes.
    return {"tracking_id": case["tracking_id"], "status": case["status"],
        "submitted_at": case["submitted_at"], "updated_at": case["updated_at"],
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
