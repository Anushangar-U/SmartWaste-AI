from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from backend.schemas import (ComplaintRequest, AnalysisResult, RetrievalRequest,
                             RetrievalResult, DecisionRequest, DecisionResult, FinalResponse)
from backend.auth.dependencies import require_role
from backend.services import agent_client
from backend.services import cases

router = APIRouter(tags=["agents"])

# Full pipeline: this is what the frontend calls
@router.post("/complaints/process", response_model=FinalResponse)
def process(body: ComplaintRequest, idempotency_key: str | None = Header(default=None, min_length=16, max_length=128)):
    case, _ = cases.submit(body.text, body.location_context, idempotency_key,
        body.clarification_answers.model_dump() if body.clarification_answers else None, body.area)
    if case["status"] in {"processing_failed", "processing", "submitted"}:
        return JSONResponse(status_code=502, content={"detail": "Complaint saved; automated processing is unavailable.",
            "tracking_id": case["tracking_id"]})
    if not all(case.get(field) for field in ["analysis", "retrieval", "decision", "validation"]):
        return JSONResponse(status_code=202, content=cases.public_status(case))
    return FinalResponse(request_id=case["id"], analysis=case["analysis"], retrieval=case["retrieval"],
        decision=case["decision"], validation=case["validation"])

# Individual agent endpoints: for debugging, testing, and showing the JSON in the demo
@router.post("/agents/analyze", response_model=AnalysisResult)
def analyze(body: ComplaintRequest, user: dict = Depends(require_role("admin"))):
    return agent_client.call_analyst(body.text)

@router.post("/agents/retrieve", response_model=RetrievalResult)
def retrieve(body: RetrievalRequest, user: dict = Depends(require_role("admin"))):
    return agent_client.call_retrieval(body.analysis)

@router.post("/agents/decide", response_model=DecisionResult)
def decide(body: DecisionRequest, user: dict = Depends(require_role("admin"))):
    return agent_client.call_decision(body.analysis, body.retrieval)
