"""Advisory image analysis and conservative text/image reconciliation."""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from backend.config import settings
from backend.services.provider_failover import (
    has_openrouter_credentials,
    openrouter_chat_create,
)
from backend.schemas import ImageAnalysisResult


class VisionProviderError(RuntimeError):
    pass


SYSTEM_PROMPT = """You are the image-analysis component of SmartWaste AI.
Analyze only what is visibly supported by the supplied waste photo.
Return JSON only with these keys:
visible_waste_types, visible_hazards, scene_summary, severity_hint,
confidence, uncertainty_notes.

Rules:
- Do not identify people or infer private/sensitive attributes.
- Do not invent hidden hazards, chemicals, laws, locations or quantities.
- visible_hazards should contain only hazards that appear visually plausible.
- severity_hint must be low, medium, high or unknown.
- confidence is model-reported confidence from 0 to 1, not a calibrated probability.
- If the image is unclear or unrelated, say so in uncertainty_notes and use unknown where needed.
"""


def _mock_analysis() -> ImageAnalysisResult:
    return ImageAnalysisResult(
        visible_waste_types=["mixed waste"],
        visible_hazards=[],
        scene_summary="Synthetic demo observation for an uploaded waste photo.",
        severity_hint="medium",
        confidence=0.80,
        uncertainty_notes=[
            "Synthetic demo output; no live vision provider inspected the image."
        ],
        analyzed=True,
        provider="mock_demo",
    )


def _json_text(content: str) -> str:
    cleaned = content.strip()
    fence = chr(96) * 3
    if cleaned.startswith(fence):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    if cleaned.lower().startswith("json\n"):
        cleaned = cleaned[5:].strip()
    return cleaned


def analyze_image(path: str) -> ImageAnalysisResult:
    if settings.use_mock_agents:
        return _mock_analysis()

    if not has_openrouter_credentials():
        raise VisionProviderError("Vision provider credential is not configured.")
    if not settings.vision_model:
        raise VisionProviderError("VISION_MODEL is not configured.")

    try:
        image_bytes = Path(path).read_bytes()
        data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        response = openrouter_chat_create(
            request={
                "model": settings.vision_model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Inspect this complaint photo. Return the requested JSON. "
                                    "Treat the image as advisory evidence only."
                                ),
                            },
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Vision provider returned an empty response.")
        data = json.loads(_json_text(content))
        return ImageAnalysisResult.model_validate(
            {**data, "analyzed": True, "provider": f"openrouter:{settings.vision_model}"}
        )
    except Exception as exc:
        raise VisionProviderError("Vision analysis failed.") from exc


def unavailable_analysis() -> ImageAnalysisResult:
    return ImageAnalysisResult(
        visible_waste_types=[],
        visible_hazards=[],
        scene_summary="Image analysis was unavailable. Staff can still inspect the uploaded photo.",
        severity_hint="unknown",
        confidence=0.0,
        uncertainty_notes=[
            "The image was stored, but automated image analysis did not complete."
        ],
        analyzed=False,
        provider=None,
    )


def reconcile(
    analysis: ImageAnalysisResult,
    clarification_answers: dict | None = None,
    complaint_text: str | None = None,
) -> ImageAnalysisResult:
    answers = clarification_answers or {}
    reasons = list(analysis.review_reasons)
    text = (complaint_text or "").lower()
    explicit_denial = bool(
        re.search(
            r"\b(?:no|not|without)\b.{0,50}\b(?:hazard(?:ous)?|medical|chemical|syringe|sharps?)\b",
            text,
        )
    )
    conflict = bool(
        analysis.analyzed
        and analysis.visible_hazards
        and (answers.get("hazards") == "none observed" or explicit_denial)
    )
    if conflict:
        reasons.append(
            "Reporter text or hazard selection denies visible hazards, while the image model flagged a possible visible hazard."
        )
    if analysis.visible_hazards:
        reasons.append("Possible visible image hazard requires staff verification.")
    if not analysis.analyzed:
        reasons.append("Automated image analysis was unavailable; staff should inspect the photo.")

    return analysis.model_copy(
        update={
            "image_text_conflict": conflict,
            "review_reasons": list(dict.fromkeys(reasons)),
        }
    )


def retrieval_hint(analysis: dict | ImageAnalysisResult | None) -> str | None:
    if not analysis:
        return None
    parsed = analysis if isinstance(analysis, ImageAnalysisResult) else ImageAnalysisResult.model_validate(analysis)
    if not parsed.analyzed or parsed.confidence < 0.40:
        return None

    parts = []
    if parsed.visible_waste_types:
        parts.append("visible waste: " + ", ".join(parsed.visible_waste_types[:5]))
    if parsed.visible_hazards:
        parts.append("possible visible hazards: " + ", ".join(parsed.visible_hazards[:5]))
    summary = parsed.scene_summary.strip()
    if summary:
        parts.append("scene: " + summary[:300])
    return "; ".join(parts) if parts else None


def review_requirements(analysis: dict | None) -> dict:
    if not analysis:
        return {"requires_human_review": False, "review_urgency": "normal", "warnings": []}

    parsed = ImageAnalysisResult.model_validate(analysis)
    urgency = "normal"
    warnings = list(parsed.review_reasons)

    if not parsed.analyzed:
        urgency = "elevated"
    if parsed.visible_hazards:
        urgency = "elevated"
    if parsed.image_text_conflict or parsed.severity_hint == "high":
        urgency = "urgent"

    return {
        "requires_human_review": bool(warnings),
        "review_urgency": urgency,
        "warnings": warnings,
    }
