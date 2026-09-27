"""
Quick manual checks for agents/decision/rules.py — no Groq API key needed.

Run with: python -m tests.test_rules_no_api
"""

from agents.decision.rules import validate_decision


def show(title, decision, evidence, analysis=None):
    result, issues = validate_decision(decision, evidence, analysis=analysis)
    print(f"\n--- {title} ---")
    print("Result:", result)
    print("Issues:", issues if issues else "(none)")


# 1. A well-formed decision with matching evidence — should pass clean.
show(
    "Valid decision, matches evidence",
    decision={
        "priority": "high",
        "recommended_action": "Dispatch collection crew within 24 hours.",
        "explanation": "Waste has been uncollected for 5 days near a school.",
        "supporting_sources": ["Waste Collection Guidelines"],
        "requires_human_review": False,
        "confidence": 0.85,
    },
    evidence=[
        {"source": "Waste Collection Guidelines", "snippet": "..."},
    ],
)

# 2. Invalid priority value — should be forced to "medium".
show(
    "Invalid priority string",
    decision={
        "priority": "super-urgent",
        "recommended_action": "Send a team.",
        "explanation": "It's bad.",
        "supporting_sources": [],
        "requires_human_review": False,
        "confidence": 0.9,
    },
    evidence=[],
)

# 3. Model invents a source that was never retrieved — should be stripped out.
show(
    "Fabricated citation",
    decision={
        "priority": "medium",
        "recommended_action": "Investigate further.",
        "explanation": "Based on municipal code section 4.2.",
        "supporting_sources": ["Municipal Code Section 4.2 (made up)"],
        "requires_human_review": False,
        "confidence": 0.8,
    },
    evidence=[
        {"source": "Waste Collection Guidelines", "snippet": "..."},
    ],
)

# 4. Low confidence — should force human review even if model said False.
show(
    "Low confidence forces human review",
    decision={
        "priority": "low",
        "recommended_action": "Monitor the situation.",
        "explanation": "Unclear complaint details.",
        "supporting_sources": [],
        "requires_human_review": False,
        "confidence": 0.3,
    },
    evidence=[],
)

# 5. Hazardous keyword in complaint analysis should force human review.
show(
    "Hazardous keyword triggers human review",
    decision={
        "priority": "high",
        "recommended_action": "Contact hazmat team.",
        "explanation": "Complaint mentions a possible chemical spill near the site.",
        "supporting_sources": [],
        "requires_human_review": False,
        "confidence": 0.9,
    },
    evidence=[],
    analysis={"waste_types": ["chemical"]},
)

# 6. No evidence at all — should force human review.
show(
    "Missing evidence forces human review",
    decision={
        "priority": "medium",
        "recommended_action": "Send inspector.",
        "explanation": "No supporting documents were found.",
        "supporting_sources": [],
        "requires_human_review": False,
        "confidence": 0.75,
    },
    evidence=[],
)

# 7. Missing required fields entirely — should list them and fill defaults.
show(
    "Missing required fields",
    decision={"priority": "high"},
    evidence=[],
)

print("\nAll checks ran. Review the 'Issues' lines above against what you'd expect.")
