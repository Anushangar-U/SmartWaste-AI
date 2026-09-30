import json
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from backend.auth.dependencies import require_role
from backend.schemas import ClarificationAnswers, ComplaintRequest, PublicComplaintRequest, StructuredIntake, Priority
from backend.repositories import complaints as repo
from backend.repositories import images as image_repo
from backend.services import cases

router = APIRouter(tags=["complaints"])
staff = require_role("admin", "staff")


@router.get("/staff/dashboard")
def dashboard(user=Depends(staff)):
    from backend.services.dashboard import summary
    return summary()


class ReviewRequest(BaseModel):
    version: int = Field(ge=0)
    decision: Literal["approve", "override"]
    reason: str = Field(min_length=3, max_length=2000)
    priority: Priority | None = None
    action: str | None = Field(default=None, min_length=3, max_length=2000)


class AssignmentRequest(BaseModel):
    version: int = Field(ge=0)
    assignee: str = Field(min_length=2, max_length=120)


class ResolutionRequest(BaseModel):
    version: int = Field(ge=0)
    note: str = Field(min_length=3, max_length=2000)


def find_case(identity):
    case = repo.get(identity)
    if not case:
        raise HTTPException(404, "Complaint not found")
    return case


@router.post("/complaints", status_code=201)
def submit(body: ComplaintRequest, idempotency_key: str | None = Header(default=None, min_length=16, max_length=128)):
    case, _ = cases.submit(body.text, body.location_context, idempotency_key,
        body.clarification_answers.model_dump() if body.clarification_answers else None, body.area)
    return cases.public_status(case)



@router.post("/complaints/structured", status_code=201)
def submit_structured(
    body: PublicComplaintRequest,
    idempotency_key: str | None = Header(default=None, min_length=16, max_length=128),
):
    case, _ = cases.submit_structured(
        body.text,
        body.intake,
        idempotency_key,
    )
    return cases.public_status(case)


@router.post("/complaints/structured-with-photo", status_code=201)
async def submit_structured_with_photo(
    text: str = Form(...),
    intake_json: str = Form(...),
    photo: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, min_length=16, max_length=128),
):
    try:
        intake = StructuredIntake.model_validate(json.loads(intake_json))
        body = PublicComplaintRequest(text=text, intake=intake)
    except (json.JSONDecodeError, ValidationError, TypeError):
        raise HTTPException(422, "Structured complaint details are invalid or incomplete.") from None

    raw = await photo.read()
    from backend.services.image_storage import ImageValidationError
    try:
        case, _ = cases.submit_structured_with_photo(
            body.text,
            body.intake,
            raw,
            photo.content_type,
            idempotency_key,
        )
    except ImageValidationError as exc:
        raise HTTPException(422, str(exc)) from None
    return cases.public_status(case)


@router.post("/complaints/with-photo", status_code=201)
async def submit_with_photo(
    text: str = Form(...),
    location_context: str | None = Form(default=None),
    area: str | None = Form(default=None),
    duration: str | None = Form(default=None),
    hazards: str = Form(default="unknown"),
    photo: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, min_length=16, max_length=128),
):
    answers = ClarificationAnswers(
        duration=(duration or "").strip() or None,
        hazards=hazards,
    )
    body = ComplaintRequest(
        text=text,
        location_context=(location_context or "").strip() or None,
        area=(area or "").strip() or None,
        clarification_answers=answers,
    )
    raw = await photo.read()
    from backend.services.image_storage import ImageValidationError
    try:
        case, _ = cases.submit_with_photo(
            body.text,
            body.location_context,
            raw,
            photo.content_type,
            idempotency_key,
            body.clarification_answers.model_dump(),
            body.area,
        )
    except ImageValidationError as exc:
        raise HTTPException(422, str(exc)) from None
    return cases.public_status(case)


@router.get("/complaints/track/{tracking_id}")
def track(tracking_id: str):
    case = repo.track(tracking_id)
    if not case:
        raise HTTPException(404, "Tracking ID not found")
    return cases.public_status(case)


@router.get("/staff/complaints")
def listing(status: cases.Status | None = None, search: str | None = Query(default=None, max_length=120),
            limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
            priority: Priority | None = None, review_needed: bool | None = None, user=Depends(staff)):
    return repo.list_cases(status.value if status else None, search, limit, offset,
        priority.value if priority else None, review_needed)


@router.get("/staff/complaints/{identity}")
def detail(identity: str, user=Depends(staff)):
    case = find_case(identity)
    image = image_repo.get_for_complaint(identity)
    return {
        **case,
        "photo": image_repo.staff_metadata(image),
        "history": repo.events(identity),
    }


@router.get("/staff/complaints/{identity}/photo")
def photo(identity: str, user=Depends(staff)):
    find_case(identity)
    image = image_repo.get_for_complaint(identity)
    if not image:
        raise HTTPException(404, "Complaint photo not found")
    from backend.services.image_storage import safe_path

    try:
        path = safe_path(image["stored_path"])
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "Complaint photo not found") from None
    return FileResponse(
        path,
        media_type=image["mime_type"],
        filename="complaint-photo.jpg",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/staff/complaints/{identity}/review")
def review(identity: str, body: ReviewRequest, user=Depends(staff)):
    return cases.review(find_case(identity), body, user["username"])


@router.post("/staff/complaints/{identity}/assign")
def assign(identity: str, body: AssignmentRequest, user=Depends(staff)):
    find_case(identity)
    return repo.update(identity, {"status": cases.Status.assigned.value, "assignee": body.assignee},
        version=body.version, allowed={cases.Status.reviewed.value}, event="assigned", actor=user["username"])


@router.post("/staff/complaints/{identity}/resolve")
def resolve(identity: str, body: ResolutionRequest, user=Depends(staff)):
    find_case(identity)
    return repo.update(identity, {"status": cases.Status.resolved.value, "resolution_note": body.note,
        "resolved_at": repo.now()}, version=body.version, allowed={cases.Status.assigned.value},
        event="resolved", actor=user["username"], note=body.note)


@router.post("/staff/complaints/{identity}/retry")
def retry(identity: str, user=Depends(staff)):
    return cases.process(find_case(identity))


class DuplicateConfirmation(BaseModel):
    other_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=3, max_length=1000)


@router.get("/staff/complaints/{identity}/duplicates")
def duplicates(identity: str, user=Depends(staff)):
    from backend.services.duplicates import suggestions
    return suggestions(find_case(identity))


@router.post("/staff/complaints/{identity}/duplicate")
def confirm_duplicate(identity: str, body: DuplicateConfirmation, user=Depends(staff)):
    from backend.services.duplicates import confirm
    find_case(identity)
    find_case(body.other_id)
    return confirm(identity, body.other_id, user["username"], body.reason)
