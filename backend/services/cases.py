from enum import Enum
from datetime import datetime, timezone

from backend.config import settings
from backend.repositories import complaints as repo
from backend.repositories import images as image_repo
from backend.services.orchestrator import process_complaint, AgentError


class Status(str, Enum):
    submitted = "submitted"
    processing = "processing"
    awaiting_review = "awaiting_review"
    reviewed = "reviewed"
    assigned = "assigned"
    processing_failed = "processing_failed"
    resolved = "resolved"


_URGENCY_ORDER = {"normal": 0, "elevated": 1, "urgent": 2}


def _stronger_urgency(first: str | None, second: str | None) -> str:
    first = first if first in _URGENCY_ORDER else "normal"
    second = second if second in _URGENCY_ORDER else "normal"
    return first if _URGENCY_ORDER[first] >= _URGENCY_ORDER[second] else second


def _reporter_review_urgency(text: str, answers=None) -> str:
    from agents.decision.triage import hazard_mentions

    affirmative, uncertain = hazard_mentions(text)
    if affirmative or (answers or {}).get("hazards") == "visible":
        return "urgent"
    if uncertain:
        return "elevated"
    return "normal"


def process(case):
    from backend.middleware.resources import processing_slot

    with processing_slot() as admitted:
        if not admitted:
            return repo.update(
                case["id"],
                {
                    "status": Status.processing_failed.value,
                    "error_stage": "capacity",
                    "requires_human_review": True,
                },
                version=case["version"],
                allowed={Status.submitted.value, Status.processing_failed.value},
                event="capacity_unavailable",
            )
        return _process(case)


def _process(case):
    mode = "mock_demo" if settings.use_mock_agents else "live"
    if case.get("processing_mode") not in {None, "unknown", mode}:
        raise repo.Conflict(
            "Processing mode changed; review this case manually rather than mixing demo and live outputs."
        )

    if case["status"] == Status.processing.value:
        started = datetime.fromisoformat(case["processing_started_at"])
        if (datetime.now(timezone.utc) - started).total_seconds() <= settings.processing_lease_seconds:
            raise repo.Conflict("Processing is still active.")
        case = repo.update(
            case["id"],
            {"status": Status.processing_failed.value, "error_stage": "interrupted"},
            version=case["version"],
            event="interrupted",
        )

    if case["processing_attempts"] >= settings.processing_max_attempts:
        raise repo.Conflict("Processing retry limit reached; use manual review.")

    case = repo.update(
        case["id"],
        {
            "status": Status.processing.value,
            "processing_started_at": repo.now(),
            "error_stage": None,
            "processing_attempts": case["processing_attempts"] + 1,
        },
        version=case["version"],
        allowed={Status.submitted.value, Status.processing_failed.value},
        event="processing",
    )

    try:
        def checkpoint(field, result):
            changes = {field: result}
            if field == "analysis" and result.get("severity") == "high":
                changes["review_urgency"] = "urgent"
            repo.update(case["id"], changes, allowed={Status.processing.value})

        text = case["text"]
        structured_context = None
        if case.get("structured_intake"):
            from backend.services.citizen_guidance import structured_context as build_structured_context
            structured_context = build_structured_context(case["structured_intake"])
            if structured_context:
                text += "\n" + structured_context
        if case.get("area"):
            text += "\nReporter supplied public area: " + case["area"]

        answers = case.get("clarification_answers") or {}
        if answers.get("duration"):
            text += "\nReporter supplied duration: " + answers["duration"]
        if answers.get("hazards") == "visible":
            text += "\nReporter observes potentially hazardous material."
        elif answers.get("hazards") == "none observed":
            text += "\nReporter observes no hazardous material."

        image_record = image_repo.get_for_complaint(case["id"])
        image_analysis = (image_record or {}).get("analysis")
        image_context = None
        image_requirements = {
            "requires_human_review": False,
            "review_urgency": "normal",
            "warnings": [],
        }
        if image_analysis:
            from backend.services.vision import retrieval_hint, review_requirements

            image_context = retrieval_hint(image_analysis)
            image_requirements = review_requirements(image_analysis)

        retrieval_context = structured_context
        if image_context:
            retrieval_context = (
                (retrieval_context + " | " if retrieval_context else "")
                + "Image observations: " + image_context
            )

        result = process_complaint(
            text,
            case["location_context"],
            image_context=retrieval_context,
            resume=case,
            on_stage=checkpoint,
            request_id=case["id"],
        ).model_dump(mode="json")

        if image_requirements["requires_human_review"]:
            result["decision"]["requires_human_review"] = True
            result["decision"]["review_urgency"] = _stronger_urgency(
                result["decision"].get("review_urgency"),
                image_requirements["review_urgency"],
            )
            warnings = result["validation"].setdefault("warnings", [])
            for warning in image_requirements["warnings"]:
                if warning not in warnings:
                    warnings.append(warning)
            if image_requirements["warnings"]:
                result["validation"]["passed"] = False

        return repo.update(
            case["id"],
            {
                **{key: result[key] for key in repo.JSON_FIELDS},
                "status": Status.awaiting_review.value,
                "review_urgency": result["decision"].get("review_urgency", "normal"),
                # Every AI-assisted recommendation requires an authorized staff
                # decision before assignment. The nested decision flag remains the
                # agent's extra safety-escalation signal; this top-level flag is the
                # workflow requirement used by the staff review queue.
                "requires_human_review": True,
            },
            event="analysis_completed",
        )
    except AgentError as exc:
        return repo.update(
            case["id"],
            {
                "status": Status.processing_failed.value,
                "error_stage": exc.stage,
                "requires_human_review": True,
            },
            event="processing_failed",
        )


def submit(text, location=None, idempotency_key=None, answers=None, area=None):
    case, created = repo.create(text, location, idempotency_key, answers, area)
    if created:
        urgency = _reporter_review_urgency(text, answers)
        if urgency != "normal":
            case = repo.update(case["id"], {"review_urgency": urgency})
    return (process(case) if created else case), created



def submit_structured(text, intake, idempotency_key=None):
    """Submit the new fully structured citizen intake while preserving legacy APIs."""
    from backend.schemas import StructuredIntake
    from backend.services.citizen_guidance import build_guidance

    parsed = intake if isinstance(intake, StructuredIntake) else StructuredIntake.model_validate(intake)
    data = parsed.model_dump(mode="json")
    location = parsed.location_type.replace("_", " ")
    area = parsed.area_landmark
    answers = {
        "duration": parsed.duration.replace("_", " "),
        "hazards": "none observed" if parsed.hazards == ["none_observed"] else (
            "unknown" if parsed.hazards == ["unknown"] else "visible"
        ),
    }
    case, created = repo.create(
        text,
        location,
        idempotency_key,
        answers,
        area,
        intake=data,
    )
    if created:
        guidance = build_guidance(parsed).model_dump(mode="json")
        urgency = _reporter_review_urgency(text, answers)
        if guidance["risk_level"] == "high":
            urgency = "urgent"
        elif guidance["risk_level"] == "elevated":
            urgency = _stronger_urgency(urgency, "elevated")
        case = repo.update(
            case["id"],
            {"citizen_guidance": guidance, "review_urgency": urgency},
        )
    return (process(case) if created else case), created


def submit_structured_with_photo(
    text,
    intake,
    raw_image: bytes,
    declared_mime: str | None,
    idempotency_key=None,
):
    """Structured intake plus optional advisory image analysis."""
    from backend.schemas import StructuredIntake
    from backend.services import image_storage, vision
    from backend.services.citizen_guidance import build_guidance

    parsed = intake if isinstance(intake, StructuredIntake) else StructuredIntake.model_validate(intake)
    data = parsed.model_dump(mode="json")
    sanitized = image_storage.sanitize_image(raw_image, declared_mime)
    answers = {
        "duration": parsed.duration.replace("_", " "),
        "hazards": "none observed" if parsed.hazards == ["none_observed"] else (
            "unknown" if parsed.hazards == ["unknown"] else "visible"
        ),
    }
    case, created = repo.create(
        text,
        parsed.location_type.replace("_", " "),
        idempotency_key,
        answers,
        parsed.area_landmark,
        intake=data,
    )
    if not created:
        existing = image_repo.get_for_complaint(case["id"])
        if not existing or existing["sha256"] != sanitized["sha256"]:
            raise repo.Conflict(
                "The idempotency key is already associated with a different submission or photo."
            )
        return case, False

    guidance = build_guidance(parsed).model_dump(mode="json")
    case = repo.update(case["id"], {"citizen_guidance": guidance})

    stored = None
    try:
        stored = image_storage.persist_image(sanitized)
        image_repo.create(case["id"], **stored)
    except Exception:
        if stored:
            image_storage.remove_file(stored.get("stored_path"))
        raise

    try:
        image_analysis = vision.reconcile(
            vision.analyze_image(stored["stored_path"]),
            answers,
            text,
        )
        image_repo.set_analysis(case["id"], image_analysis.model_dump(mode="json"))
    except vision.VisionProviderError:
        image_analysis = vision.reconcile(vision.unavailable_analysis(), answers, text)
        image_repo.set_analysis(
            case["id"],
            image_analysis.model_dump(mode="json"),
            analysis_error="vision_unavailable",
        )

    reporter_urgency = _reporter_review_urgency(text, answers)
    guidance_urgency = "urgent" if guidance["risk_level"] == "high" else (
        "elevated" if guidance["risk_level"] == "elevated" else "normal"
    )
    image_urgency = vision.review_requirements(
        image_analysis.model_dump(mode="json")
    )["review_urgency"]
    urgency = _stronger_urgency(
        _stronger_urgency(reporter_urgency, guidance_urgency),
        image_urgency,
    )
    case = repo.update(case["id"], {"review_urgency": urgency})
    return process(case), True


def submit_with_photo(
    text,
    location,
    raw_image: bytes,
    declared_mime: str | None,
    idempotency_key=None,
    answers=None,
    area=None,
):
    """Persist the complaint and sanitized image before any external AI call."""
    from backend.services import image_storage, vision

    sanitized = image_storage.sanitize_image(raw_image, declared_mime)
    case, created = repo.create(text, location, idempotency_key, answers, area)

    if not created:
        existing = image_repo.get_for_complaint(case["id"])
        if not existing or existing["sha256"] != sanitized["sha256"]:
            raise repo.Conflict(
                "The idempotency key is already associated with a different submission or photo."
            )
        return case, False

    stored = None
    try:
        stored = image_storage.persist_image(sanitized)
        image_repo.create(case["id"], **stored)
    except Exception:
        if stored:
            image_storage.remove_file(stored.get("stored_path"))
        raise

    try:
        image_analysis = vision.reconcile(vision.analyze_image(stored["stored_path"]), answers, text)
        image_repo.set_analysis(case["id"], image_analysis.model_dump(mode="json"))
    except vision.VisionProviderError:
        image_analysis = vision.reconcile(vision.unavailable_analysis(), answers, text)
        image_repo.set_analysis(
            case["id"],
            image_analysis.model_dump(mode="json"),
            analysis_error="vision_unavailable",
        )

    reporter_urgency = _reporter_review_urgency(text, answers)
    image_urgency = vision.review_requirements(
        image_analysis.model_dump(mode="json")
    )["review_urgency"]
    urgency = _stronger_urgency(reporter_urgency, image_urgency)
    if urgency != "normal":
        case = repo.update(case["id"], {"review_urgency": urgency})

    return process(case), True


def public_status(case):
    # Explicit allowlist: never expose complaint text, image paths, provider errors or staff notes.
    return {
        "tracking_id": case["tracking_id"],
        "status": case["status"],
        "mode": case.get("processing_mode", "unknown"),
        "submitted_at": case["submitted_at"],
        "updated_at": case["updated_at"],
        "clarification_questions": (case.get("decision") or {}).get(
            "clarification_questions", []
        ),
        "guidance": case.get("citizen_guidance"),
        "message": (
            "Your complaint is saved. Staff can review it even when automated processing is unavailable."
        ),
        "history": [
            {"status": event["status"], "at": event["created_at"]}
            for event in repo.events(case["id"])
        ],
    }


def review(case, body, actor):
    if body.decision == "approve":
        if not case["decision"] or case["status"] != Status.awaiting_review.value:
            raise repo.Conflict("No AI recommendation exists; use an explicit manual override.")
        priority, action = (
            case["decision"]["priority"],
            case["decision"]["recommended_action"],
        )
    else:
        if not body.priority or not body.action:
            raise repo.Conflict("Override requires a priority and action.")
        priority, action = body.priority.value, body.action

    return repo.update(
        case["id"],
        {
            "status": Status.reviewed.value,
            "reviewer": actor,
            "review_decision": body.decision,
            "review_reason": body.reason,
            "reviewed_at": repo.now(),
            "human_priority": priority,
            "human_action": action,
            "requires_human_review": False,
        },
        version=body.version,
        allowed={Status.awaiting_review.value, Status.processing_failed.value},
        event="reviewed",
        actor=actor,
        note=body.reason,
    )
