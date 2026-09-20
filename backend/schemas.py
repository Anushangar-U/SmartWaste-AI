from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

# ---------- Frontend -> Backend ----------
class ComplaintRequest(BaseModel):
    text: str = Field(min_length=10, max_length=2000)

# ---------- Agent 1 output (Gemini) ----------
class AnalysisResult(BaseModel):
    waste_types: List[str]
    location: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=0, le=3650)
    severity: Severity
    issue_type: str = "unknown"
    summary: str = ""

# ---------- Agent 2 ----------
class RetrievalRequest(BaseModel):
    analysis: AnalysisResult

class RetrievalResult(BaseModel):
    sources: List[str]
    evidence: List[str]

# ---------- Agent 3 ----------
class DecisionRequest(BaseModel):
    analysis: AnalysisResult
    retrieval: RetrievalResult

class DecisionResult(BaseModel):
    priority: Priority
    recommendation: str
    explanation: str = ""
    sources: List[str] = []
    human_review: bool = True

# ---------- Validation + final response ----------
class ValidationReport(BaseModel):
    passed: bool
    warnings: List[str] = []

class FinalResponse(BaseModel):
    request_id: str
    analysis: AnalysisResult
    retrieval: RetrievalResult
    decision: DecisionResult
    validation: ValidationReport
    disclaimer: str = "AI-generated recommendation. Final decisions must be made by authorized staff."

# ---------- Auth ----------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=72)   # bcrypt limit is 72 bytes

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"