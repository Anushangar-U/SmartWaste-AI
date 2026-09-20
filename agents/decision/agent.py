"""
Agent 3 - Decision & Recommendation Agent (now powered by Groq's free API).

Exposes `decide(analysis, evidence)` which the FastAPI backend calls from
the POST /agents/decide endpoint. Keeps the API call, JSON parsing, and
Responsible-AI validation in one place so Member 3's backend just needs to
import `decide`.

Groq uses the same "chat" message format as OpenAI: a list of
{"role": ..., "content": ...} dicts, with role "system" for instructions
and role "user" for the actual request. That's the one structural
difference from calling Claude (which takes system as a separate field).
"""

import json
import os

from groq import Groq

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .rules import validate_decision

# Default model can be overridden via env var without touching code.
# llama-3.3-70b-versatile is Groq's recommended general-purpose chat model.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file. "
                "Get a free key at https://console.groq.com/keys"
            )
        _client = Groq(api_key=api_key)
    return _client


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from the model's reply."""
    text = text.strip()
    # Strip markdown code fences if the model added them anyway.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {text!r}")
    return json.loads(text[start : end + 1])


def decide(analysis: dict, evidence: list) -> dict:
    """
    Calls Groq to produce a decision, then runs it through the
    Responsible-AI validation layer before returning it.

    Returns a dict shaped like DECISION_OUTPUT_SCHEMA in prompts.py, plus a
    "validation" key describing any issues the rules layer caught.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1024,
        # Groq's free tier can be a little less obedient about "JSON only"
        # than larger hosted models, so we lower temperature for consistency.
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(analysis, evidence)},
        ],
    )

    raw_text = response.choices[0].message.content

    try:
        decision = _extract_json(raw_text)
    except (ValueError, json.JSONDecodeError) as exc:
        # Fail safe: never show a broken/uncertain output as if it were a
        # confident recommendation. Force human review instead.
        decision = {
            "priority": "medium",
            "recommended_action": "Manual review required — automated decision failed.",
            "explanation": f"The decision agent could not parse a valid response ({exc}).",
            "supporting_sources": [],
            "requires_human_review": True,
            "confidence": 0.0,
        }

    validated, issues = validate_decision(decision, evidence)
    validated["validation"] = {
        "passed": len(issues) == 0,
        "issues": issues,
    }
    return validated


if __name__ == "__main__":
    # Quick manual smoke test: python -m agents.decision.agent
    sample_analysis = {
        "waste_types": ["organic", "plastic"],
        "location": "behind school",
        "duration_days": 5,
        "severity": "high",
        "issue_type": "uncollected waste",
        "summary": "Mixed organic and plastic waste has remained near a school for five days.",
    }
    sample_evidence = [
        {
            "source": "Waste Collection Guidelines",
            "snippet": "Uncollected waste near schools for more than 3 days should be prioritized for immediate collection due to health risk.",
        }
    ]
    print(json.dumps(decide(sample_analysis, sample_evidence), indent=2))
