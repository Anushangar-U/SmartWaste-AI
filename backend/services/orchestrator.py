import logging, time, uuid
from backend.schemas import FinalResponse
from backend.services import agent_client
from backend.services.validator import validate

log = logging.getLogger("smartwaste.orchestrator")

class AgentError(Exception):
    def __init__(self, stage: str):
        self.stage = stage

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

def process_complaint(text: str) -> FinalResponse:
    request_id = str(uuid.uuid4())[:8]
    log.info("request_id=%s pipeline=start", request_id)

    analysis  = _run("analyst",   agent_client.call_analyst, text)
    retrieval = _run("retrieval", agent_client.call_retrieval, analysis)
    decision  = _run("decision",  agent_client.call_decision, analysis, retrieval)
    report    = validate(analysis, retrieval, decision)

    log.info("request_id=%s pipeline=done validation_passed=%s", request_id, report.passed)
    return FinalResponse(request_id=request_id, analysis=analysis,
                         retrieval=retrieval, decision=decision, validation=report)