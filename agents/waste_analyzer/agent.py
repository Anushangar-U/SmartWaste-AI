import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .schemas import WasteAnalysis


load_dotenv()

AGENT1_OPENROUTER_API_KEY = os.getenv("AGENT1_OPENROUTER_API_KEY")
AGENT1_OPENROUTER_MODEL = os.getenv(
    "AGENT1_OPENROUTER_MODEL",
    "nex-agi/nex-n2.5-mini:free",
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_openrouter_client: OpenAI | None = None
_gemini_client: genai.Client | None = None


def _get_openrouter_client() -> OpenAI:
    global _openrouter_client

    if not AGENT1_OPENROUTER_API_KEY:
        raise RuntimeError("AGENT1_OPENROUTER_API_KEY is not configured.")

    if _openrouter_client is None:
        _openrouter_client = OpenAI(
            api_key=AGENT1_OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    return _openrouter_client


def _get_gemini_client() -> genai.Client:
    global _gemini_client

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "No Agent 1 provider is configured. Set "
            "AGENT1_OPENROUTER_API_KEY or GEMINI_API_KEY."
        )

    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)

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
    response = _get_gemini_client().models.generate_content(
        model="gemini-3.6-flash",
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

    if AGENT1_OPENROUTER_API_KEY:
        return _analyze_with_openrouter(complaint)

    return _analyze_with_gemini(complaint)
