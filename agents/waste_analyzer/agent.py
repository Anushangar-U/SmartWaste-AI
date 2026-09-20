import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import SYSTEM_PROMPT
from .schemas import WasteAnalysis


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not configured. "
        "Please add it to the .env file."
    )


client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_complaint(complaint: str) -> WasteAnalysis:
    """
    Analyze a waste complaint using Gemini.

    Args:
        complaint: Natural-language waste complaint.

    Returns:
        A structured WasteAnalysis object.
    """

    if not complaint or not complaint.strip():
        raise ValueError("Complaint cannot be empty.")

    response = client.models.generate_content(
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