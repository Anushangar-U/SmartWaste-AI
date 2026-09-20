from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ComplaintRequest(BaseModel):
    text: str = Field(min_length=10, max_length=2000)


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


class EvidenceItem(BaseModel):
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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
