from backend.schemas import (AnalysisResult, RetrievalResult,
                             DecisionResult, ValidationReport, Severity)

def validate(analysis: AnalysisResult,
             retrieval: RetrievalResult,
             decision: DecisionResult) -> ValidationReport:
    warnings = []

    if not retrieval.evidence:
        warnings.append("No supporting evidence retrieved; recommendation is unsupported.")
        decision.human_review = True

    if not decision.recommendation.strip():
        warnings.append("Empty recommendation.")
        decision.human_review = True

    unknown = set(decision.sources) - set(retrieval.sources)
    if unknown:
        warnings.append(f"Recommendation cites sources not retrieved: {sorted(unknown)}")
        decision.human_review = True

    if analysis.severity == Severity.high and not decision.human_review:
        decision.human_review = True   # high-risk cases always need a human

    return ValidationReport(passed=len(warnings) == 0, warnings=warnings)