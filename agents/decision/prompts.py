"""
Prompts for Agent 3 - Decision & Recommendation Agent (Claude).

Input to this agent (from the backend orchestrator) is a dict shaped like:
{
    "analysis": {                      # output of Agent 1 (Gemini)
        "waste_types": ["organic", "plastic"],
        "location": "behind school",
        "duration_days": 5,
        "severity": "high",
        "issue_type": "uncollected waste",
        "summary": "Mixed organic and plastic waste has remained near a school for five days."
    },
    "evidence": [                      # output of Agent 2 (GPT + RAG)
        {
            "source": "Waste Collection Guidelines v1",
            "snippet": "Uncollected organic waste near schools should be treated as high priority...",
        },
        ...
    ]
}

Output of this agent must be strict JSON matching DECISION_OUTPUT_SCHEMA below.
"""

DECISION_OUTPUT_SCHEMA = {
    "priority": "one of: low | medium | high | critical",
    "recommended_action": "short, concrete action for the operations team",
    "explanation": "plain-language reasoning citing the analysis and evidence",
    "supporting_sources": "list of source names/ids drawn from the evidence provided",
    "requires_human_review": "boolean - true for ambiguous, high-risk, or low-confidence cases",
    "confidence": "float between 0 and 1",
}

SYSTEM_PROMPT = """You are the Decision & Recommendation Agent in SmartWaste AI, a multi-agent \
system that helps waste-management staff triage citizen complaints.

You will be given:
1. A structured analysis of a complaint (waste types, location, duration, severity, issue type).
2. A list of evidence snippets retrieved from an internal waste-management knowledge base.

Your job:
- Decide a priority level: "low", "medium", "high", or "critical".
- Recommend one concrete, actionable next step for the operations team.
- Explain the recommendation in plain language, explicitly referencing which
  parts of the analysis and which evidence sources drove the decision.
- List the supporting source names you actually relied on (only from the
  evidence you were given — never invent a source).
- Set requires_human_review to true whenever: evidence is missing or weak,
  the case involves potential hazardous/health risk, the case is ambiguous,
  or your confidence is below 0.6.
- Base priority ONLY on objective factors: duration, severity, waste type,
  environmental/health risk, and location characteristics (e.g. school,
  hospital, water source nearby). NEVER use socioeconomic status, religion,
  ethnicity, gender, or any other protected/unrelated personal characteristic
  as a factor, even if such information appears in the input.
- If the input analysis or evidence looks incomplete or contradictory, say so
  in the explanation and prefer flagging requires_human_review over guessing.

Respond with ONLY a single JSON object, no prose before or after, with exactly
these fields: priority, recommended_action, explanation, supporting_sources,
requires_human_review, confidence.
"""


def build_user_prompt(analysis: dict, evidence: list) -> str:
    """Builds the user-turn content sent to Claude for a single complaint."""
    evidence_block = "\n".join(
        f"- [{item.get('source', 'unknown source')}] {item.get('snippet', '')}"
        for item in evidence
    ) or "(no evidence retrieved)"

    return f"""Complaint analysis (from Agent 1):
{analysis}

Retrieved evidence (from Agent 2):
{evidence_block}

Produce the JSON decision object now.
"""
