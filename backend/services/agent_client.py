from backend.config import settings
from backend.schemas import AnalysisResult, RetrievalResult, DecisionResult

def call_analyst(text: str) -> AnalysisResult:
    if settings.use_mock_agents:
        from backend.services.mock_agents import analyze
    else:
        from agents.analyst.agent import analyze
    return AnalysisResult(**analyze(text))

def call_retrieval(analysis: AnalysisResult) -> RetrievalResult:
    if settings.use_mock_agents:
        from backend.services.mock_agents import retrieve
    else:
        from agents.knowledge.agent import retrieve
    return RetrievalResult(**retrieve(analysis.model_dump()))

def call_decision(analysis: AnalysisResult, retrieval: RetrievalResult) -> DecisionResult:
    if settings.use_mock_agents:
        from backend.services.mock_agents import decide
    else:
        from agents.decision.agent import decide
    return DecisionResult(**decide(analysis.model_dump(), retrieval.model_dump()))