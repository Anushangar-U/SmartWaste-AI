from fastapi import APIRouter, Depends
from backend.schemas import (ComplaintRequest, AnalysisResult, RetrievalRequest,
                             RetrievalResult, DecisionRequest, DecisionResult, FinalResponse)
from backend.auth.dependencies import get_current_user, require_role
from backend.services import agent_client, orchestrator

router = APIRouter(tags=["agents"])

# Full pipeline: this is what the frontend calls
@router.post("/complaints/process", response_model=FinalResponse)
def process(body: ComplaintRequest, user: dict = Depends(get_current_user)):
    return orchestrator.process_complaint(body.text)

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