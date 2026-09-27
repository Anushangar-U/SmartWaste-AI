import logging, time, uuid
from backend.schemas import FinalResponse, AnalysisResult, RetrievalResult, DecisionResult
from backend.services import agent_client
from backend.services.validator import validate

log = logging.getLogger("smartwaste.orchestrator")

class AgentError(Exception):
    def __init__(self, stage: str):
        self.stage = stage


LOCATION_TERMS = {
    "residential street": ("residential", "street"),
    "near a school": ("school",),
    "near a hospital / clinic": ("hospital", "clinic"),
    "commercial area": ("commercial", "shop", "market"),
    "industrial area": ("industrial", "factory"),
    "near a water source (river/canal/lake)": ("river", "canal", "lake", "water source"),
    "public park": ("park",),
}


def with_location_context(text: str, location_context: str | None) -> str:
    location = (location_context or "").strip()
    if not location or location.lower() == "other":
        return text
    terms = LOCATION_TERMS.get(location.lower(), (location.lower(),))
    if any(term in text.lower() for term in terms):
        return text
    return f"{text}\nLocation type selected by reporter: {location}."


def _run(stage: str, fn, *args):
    start = time.perf_counter()
    try:
        result = fn(*args)
        log.info("stage=%s status=ok ms=%d", stage, (time.perf_counter() - start) * 1000)
        return result
    except Exception as e:
        # log the error type only; never log prompts, keys or user text
        log.error("stage=%s status=failed error=%s", stage, type(e).__name__)
        raise AgentError(stage) from e

def process_complaint(text: str, location_context: str | None = None, *, resume=None, on_stage=None, request_id=None) -> FinalResponse:
    request_id = request_id or str(uuid.uuid4())
    log.info("request_id=%s pipeline=start", request_id)

    analyst_input = with_location_context(text, location_context)
    saved = resume or {}
    def stage(name, field, schema, fn, *args):
        if saved.get(field):
            return schema.model_validate(saved[field])
        result = _run(name, fn, *args)
        if on_stage:
            on_stage(field, result.model_dump(mode="json"))
        return result
    analysis = stage("analyst", "analysis", AnalysisResult, agent_client.call_analyst, analyst_input)
    retrieval = stage("retrieval", "retrieval", RetrievalResult, agent_client.call_retrieval, analysis)
    decision = stage("decision", "decision", DecisionResult, agent_client.call_decision, analysis, retrieval, analyst_input)
    report = _run("validation", validate, analysis, retrieval, decision)

    log.info("request_id=%s pipeline=done validation_passed=%s", request_id, report.passed)
    return FinalResponse(request_id=request_id, analysis=analysis,
                         retrieval=retrieval, decision=decision, validation=report)
