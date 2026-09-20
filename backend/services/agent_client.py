from typing import Any

from backend.config import settings
from backend.schemas import AnalysisResult, DecisionResult, RetrievalResult


def _as_dict(value: Any) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"Agent returned unsupported result type: {type(value).__name__}")


def call_analyst(text: str) -> AnalysisResult:
    if settings.use_mock_agents:
        from backend.services.mock_agents import analyze

        raw_analysis = analyze(text)
    else:
        from agents.waste_analyzer.agent import analyze_complaint

        raw_analysis = analyze_complaint(text)

    return AnalysisResult.model_validate(_as_dict(raw_analysis))


def call_retrieval(analysis: AnalysisResult) -> RetrievalResult:
    if settings.use_mock_agents:
        from backend.services.mock_agents import retrieve

        raw_retrieval = retrieve(analysis.model_dump(mode="json"))
    else:
        from agents.knowledge_agent.rag_agent import generate_answer
        from agents.waste_analyzer.schemas import WasteAnalysis

        waste_analysis = WasteAnalysis.model_validate(
            analysis.model_dump(mode="json")
        )
        raw_retrieval = generate_answer(waste_analysis)

    return RetrievalResult.model_validate(_as_dict(raw_retrieval))


def call_decision(
    analysis: AnalysisResult,
    retrieval: RetrievalResult,
) -> DecisionResult:
    if settings.use_mock_agents:
        from backend.services.mock_agents import decide

        raw_decision = decide(
            analysis.model_dump(mode="json"),
            retrieval.model_dump(mode="json"),
        )
    else:
        from agents.decision.agent import decide

        agent_evidence = []
        for item in retrieval.evidence:
            evidence_item = item.model_dump(mode="json")
            evidence_item["snippet"] = evidence_item["text"]
            agent_evidence.append(evidence_item)

        raw_decision = decide(
            analysis.model_dump(mode="json"),
            agent_evidence,
            grounded_knowledge=retrieval.answer,
        )

    decision = _as_dict(raw_decision)
    priority = str(decision.get("priority", "medium")).lower()

    return DecisionResult.model_validate(
        {
            "priority": priority,
            "recommended_action": decision.get(
                "recommended_action",
                decision.get("recommendation", "Manual review required."),
            ),
            "explanation": decision.get("explanation", ""),
            "supporting_sources": decision.get(
                "supporting_sources",
                decision.get("sources", []),
            ),
            "requires_human_review": decision.get(
                "requires_human_review",
                decision.get("human_review", True),
            ),
            "confidence": decision.get("confidence", 0.0),
            "validation": decision.get(
                "validation",
                {"passed": True, "issues": []},
            ),
        }
    )
