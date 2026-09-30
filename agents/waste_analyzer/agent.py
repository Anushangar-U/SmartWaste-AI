from google import genai
from google.genai import types
from groq import Groq
from .prompts import SYSTEM_PROMPT
from .schemas import WasteAnalysis
from backend.config import settings
from backend.services.provider_failover import (
    has_openrouter_credentials,
    openrouter_chat_create,
    should_failover_provider_error,
)


AGENT1_OPENROUTER_MODEL = settings.agent1_openrouter_model

_gemini_client: genai.Client | None = None
_groq_client: Groq | None = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=int(settings.provider_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=settings.provider_max_retries + 1
                ),
            ),
        )

    return _gemini_client


def _get_groq_client() -> Groq:
    global _groq_client

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    if _groq_client is None:
        _groq_client = Groq(
            api_key=settings.groq_api_key,
            timeout=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        )

    return _groq_client


def _analyze_with_openrouter(complaint: str) -> WasteAnalysis:
    response = openrouter_chat_create(
        agent_specific_key=settings.agent1_openrouter_api_key,
        request={
            "model": AGENT1_OPENROUTER_MODEL,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "waste_analysis",
                    "strict": True,
                    "schema": WasteAnalysis.model_json_schema(),
                },
            },
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"USER COMPLAINT:\n{complaint}",
                },
            ],
        },
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenRouter returned an empty response.")

    return WasteAnalysis.model_validate_json(content)


def _analyze_with_gemini(complaint: str) -> WasteAnalysis:
    response = _get_gemini_client().models.generate_content(
        model=settings.gemini_model,
        contents=f"""
{SYSTEM_PROMPT}

USER COMPLAINT:
{complaint}
""",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WasteAnalysis,
        ),
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return WasteAnalysis.model_validate_json(response.text)


def _analyze_with_groq(complaint: str) -> WasteAnalysis:
    model = settings.agent1_groq_model.strip() or settings.groq_model
    response = _get_groq_client().chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\nReturn only a valid JSON object.",
            },
            {
                "role": "user",
                "content": f"USER COMPLAINT:\n{complaint}",
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Groq returned an empty response.")

    return WasteAnalysis.model_validate_json(content)


def _with_openrouter_fallback(primary, complaint: str, configured: bool) -> WasteAnalysis:
    """Use OpenRouter when the selected primary provider is unavailable."""
    if not configured:
        if has_openrouter_credentials(settings.agent1_openrouter_api_key):
            return _analyze_with_openrouter(complaint)
        return primary(complaint)

    try:
        return primary(complaint)
    except Exception as exc:
        if (
            should_failover_provider_error(exc)
            and has_openrouter_credentials(settings.agent1_openrouter_api_key)
        ):
            return _analyze_with_openrouter(complaint)
        raise


def analyze_complaint(complaint: str) -> WasteAnalysis:
    """
    Analyze a waste complaint using the configured Agent 1 provider.

    AGENT1_PROVIDER can be "groq", "openrouter", "gemini", or "auto".
    "auto" preserves the previous behavior: OpenRouter when configured,
    otherwise Gemini.
    """

    if not complaint or not complaint.strip():
        raise ValueError("Complaint cannot be empty.")

    provider = settings.agent1_provider.strip().lower()

    if provider == "groq":
        return _with_openrouter_fallback(
            _analyze_with_groq,
            complaint,
            bool(settings.groq_api_key.strip()),
        )
    if provider == "openrouter":
        return _analyze_with_openrouter(complaint)
    if provider == "gemini":
        return _with_openrouter_fallback(
            _analyze_with_gemini,
            complaint,
            bool(settings.gemini_api_key.strip()),
        )
    if provider != "auto":
        raise RuntimeError(
            "AGENT1_PROVIDER must be one of: auto, groq, openrouter, gemini."
        )

    if has_openrouter_credentials(settings.agent1_openrouter_api_key):
        return _analyze_with_openrouter(complaint)

    return _analyze_with_gemini(complaint)
