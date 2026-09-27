from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ClarificationAnswers(BaseModel):
    duration: str | None = Field(default=None, max_length=80)
    hazards: Literal["unknown", "visible", "none observed"] = "unknown"


class ComplaintRequest(BaseModel):
    text: str = Field(min_length=10, max_length=2000)
    location_context: Optional[str] = Field(default=None, max_length=120)
    clarification_answers: ClarificationAnswers | None = None


class AnalysisResult(BaseModel):
    waste_types: List[str]
    location: str = "unknown"
    duration_days: Optional[int] = Field(default=None, ge=0, le=3650)
    severity: Severity
    issue_type: str = "unknown"
    summary: str = ""


class SourceReference(BaseModel):
    source: str
    page: int
    source_id: str | None = None
    title: str | None = None
    issuer: str | None = None
    year: int | None = None
    jurisdiction: str | None = None


class EvidenceItem(SourceReference):
    chunk_id: str
    source: str
    page: int
    text: str
    score: float


class RetrievalRequest(BaseModel):
    analysis: AnalysisResult


class RetrievalResult(BaseModel):
    query: str
    answer: str
    grounded: bool
    sources: List[SourceReference] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    evidence_available: bool = False
    claim_verification: str = "not_independently_verified"
    citation_validation: dict | None = None


class DecisionRequest(BaseModel):
    analysis: AnalysisResult
    retrieval: RetrievalResult


class DecisionValidation(BaseModel):
    passed: bool = True
    issues: List[str] = Field(default_factory=list)


class DecisionResult(BaseModel):
    priority: Priority
    recommended_action: str
    explanation: str = ""
    supporting_sources: List[str] = Field(default_factory=list)
    requires_human_review: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    validation: DecisionValidation = Field(default_factory=DecisionValidation)
    review_urgency: Literal["normal", "elevated", "urgent"] = "normal"
    clarification_questions: List[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    passed: bool
    warnings: List[str] = Field(default_factory=list)


class FinalResponse(BaseModel):
    request_id: str
    analysis: AnalysisResult
    retrieval: RetrievalResult
    decision: DecisionResult
    validation: ValidationReport
    disclaimer: str = (
        "AI-generated recommendation. Final decisions must be made by "
        "authorized staff."
    )


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
