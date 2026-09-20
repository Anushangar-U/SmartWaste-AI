from backend.schemas import (
    AnalysisResult,
    DecisionResult,
    Priority,
    RetrievalResult,
    Severity,
    ValidationReport,
)


LOW_CONFIDENCE_THRESHOLD = 0.6


def validate(
    analysis: AnalysisResult,
    retrieval: RetrievalResult,
    decision: DecisionResult,
) -> ValidationReport:
    warnings: list[str] = []

    if not retrieval.evidence:
        warnings.append(
            "No supporting evidence retrieved; recommendation is unsupported."
        )
        decision.requires_human_review = True

    if not retrieval.grounded:
        warnings.append(
            "Agent 2 could not produce a sufficiently grounded knowledge answer."
        )
        decision.requires_human_review = True

    if not decision.recommended_action.strip():
        warnings.append("Empty recommendation.")
        decision.requires_human_review = True

    retrieved_sources = {item.source for item in retrieval.sources}
    unknown = set(decision.supporting_sources) - retrieved_sources
    if unknown:
        warnings.append(
            f"Recommendation cites sources not retrieved: {sorted(unknown)}"
        )
        decision.requires_human_review = True

    if decision.confidence < LOW_CONFIDENCE_THRESHOLD:
        warnings.append("Low-confidence recommendation requires human review.")
        decision.requires_human_review = True

    if not decision.validation.passed:
        warnings.extend(
            f"Agent 3 validation: {issue}"
            for issue in decision.validation.issues
        )
        decision.requires_human_review = True

    if analysis.severity == Severity.high or decision.priority == Priority.critical:
        decision.requires_human_review = True

    return ValidationReport(passed=not warnings, warnings=warnings)
