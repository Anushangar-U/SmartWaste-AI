import time
from google import genai
from google.genai import types
from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .schemas import WasteAnalysis
from backend.config import settings


AGENT1_OPENROUTER_MODEL = settings.agent1_openrouter_model

_openrouter_client: OpenAI | None = None
_gemini_client: genai.Client | None = None


def _get_openrouter_client() -> OpenAI:
    global _openrouter_client

    if not settings.agent1_openrouter_api_key:
        raise RuntimeError("AGENT1_OPENROUTER_API_KEY is not configured.")

    if _openrouter_client is None:
        _openrouter_client = OpenAI(
            api_key=settings.agent1_openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        )

    return _openrouter_client


def _get_gemini_client() -> genai.Client:
    global _gemini_client

    if not settings.gemini_api_key:
        raise RuntimeError(
            "No Agent 1 provider is configured. Set "
            "AGENT1_OPENROUTER_API_KEY or GEMINI_API_KEY."
        )

    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.provider_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=settings.provider_max_retries + 1)))

    return _gemini_client


def _analyze_with_openrouter(complaint: str) -> WasteAnalysis:
    response = _get_openrouter_client().chat.completions.create(
        model=AGENT1_OPENROUTER_MODEL,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "waste_analysis",
                "strict": True,
                "schema": WasteAnalysis.model_json_schema(),
            },
        },
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"USER COMPLAINT:\n{complaint}",
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenRouter returned an empty response.")

    return WasteAnalysis.model_validate_json(content)


def _analyze_with_gemini(complaint: str) -> WasteAnalysis:
    models = [
        settings.gemini_model,
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]

    last_error = None

    for model in models:
        for attempt in range(3):
            try:
                print(
                    f"Trying Gemini model: {model} "
                    f"(attempt {attempt + 1}/3)"
                )

                response = _get_gemini_client().models.generate_content(
                    model=model,
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
                    raise ValueError(
                        "Gemini returned an empty response."
                    )

                print(f"Gemini model succeeded: {model}")

                return WasteAnalysis.model_validate_json(
                    response.text
                )

            except Exception as error:
                last_error = error

                print(
                    f"Gemini request failed: {error}"
                )

                time.sleep(2 ** attempt)

        print(
            f"Model {model} failed after 3 attempts. "
            "Trying next model..."
        )

    raise RuntimeError(
        f"All Gemini models failed. Last error: {last_error}"
    )


def analyze_complaint(complaint: str) -> WasteAnalysis:
    """
    Analyze a waste complaint using the configured Agent 1 provider.

    Args:
        complaint: Natural-language waste complaint.

    Returns:
        A structured WasteAnalysis object.
    """

    if not complaint or not complaint.strip():
        raise ValueError("Complaint cannot be empty.")

    if settings.agent1_openrouter_api_key:
        return _analyze_with_openrouter(complaint)

    return _analyze_with_gemini(complaint)
