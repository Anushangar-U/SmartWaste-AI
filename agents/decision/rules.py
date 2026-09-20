"""
Validation / Responsible AI safety layer for Agent 3's output.

This runs after every Claude call, before a decision is shown to the user
(section 11 of the project plan: "Validation and AI Safety Layer").
It never talks to an LLM — it's plain Python so it's fast, deterministic,
and easy to explain in the viva.
"""

ALLOWED_PRIORITIES = {"low", "medium", "high", "critical"}
REQUIRED_FIELDS = {
    "priority",
    "recommended_action",
    "explanation",
    "supporting_sources",
    "requires_human_review",
    "confidence",
}

# Keywords that, if present in the analysis or explanation, should force
# human review regardless of what the model decided (hazardous / high-risk
# cases per the Responsible AI section of the plan).
HIGH_RISK_KEYWORDS = {
    "hazardous",
    "medical",
    "chemical",
    "toxic",
    "biohazard",
    "syringe",
    "gas leak",
    "radioactive",
}

LOW_CONFIDENCE_THRESHOLD = 0.6


def validate_decision(decision: dict, evidence: list) -> tuple[dict, list[str]]:
    """
    Checks the decision dict for completeness and Responsible-AI compliance.
    Mutates a copy of `decision` to safe defaults where needed and returns
    (decision, issues) where `issues` is a list of human-readable strings
    describing anything the raw model output got wrong.
    """
    decision = dict(decision)
    issues = []

    # 1. Required fields present.
    missing = REQUIRED_FIELDS - decision.keys()
    if missing:
        issues.append(f"Missing required fields: {sorted(missing)}")
        for field in missing:
            decision[field] = None

    # 2. Priority is one of the allowed categories.
    if decision.get("priority") not in ALLOWED_PRIORITIES:
        issues.append(
            f"Invalid priority {decision.get('priority')!r}; defaulting to 'medium'."
        )
        decision["priority"] = "medium"

    # 3. Supporting sources must actually come from the evidence provided
    #    (never let the model cite a source that wasn't retrieved).
    known_sources = {item.get("source") for item in evidence if item.get("source")}
    cited = decision.get("supporting_sources") or []
    if isinstance(cited, str):
        cited = [cited]
    valid_cited = [s for s in cited if s in known_sources]
    if len(valid_cited) != len(cited):
        issues.append(
            "Removed cited sources that weren't part of the retrieved evidence."
        )
    decision["supporting_sources"] = valid_cited

    if not evidence:
        issues.append("No evidence was retrieved for this complaint.")
        decision["requires_human_review"] = True

    # 4. Confidence must be a sane float; low confidence forces human review.
    try:
        confidence = float(decision.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
        issues.append("Confidence was missing/invalid; treated as 0.0.")
    decision["confidence"] = max(0.0, min(1.0, confidence))
    if decision["confidence"] < LOW_CONFIDENCE_THRESHOLD:
        decision["requires_human_review"] = True

    # 5. High-risk keyword sweep across explanation + recommended action.
    text_to_scan = " ".join(
        str(decision.get(field, "")) for field in ("explanation", "recommended_action")
    ).lower()
    if any(keyword in text_to_scan for keyword in HIGH_RISK_KEYWORDS):
        decision["requires_human_review"] = True
        issues.append("High-risk keyword detected; forced human review.")

    # 6. requires_human_review must be a real bool.
    decision["requires_human_review"] = bool(decision.get("requires_human_review", False))

    return decision, issues
