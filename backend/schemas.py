from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class StructuredIntake(BaseModel):
    waste_types: List[Literal[
        "household_mixed", "food_organic", "plastic", "paper_cardboard", "glass",
        "metal_sharp", "construction_debris", "e_waste", "batteries", "medical_waste",
        "sharps_needles", "chemicals", "pesticides", "paint_solvent_oil_fuel",
        "industrial_waste", "garden_waste", "animal_waste_carcass", "other", "unknown"
    ]] = Field(min_length=1, max_length=8)
    specific_items: str = Field(min_length=3, max_length=240)
    problem_type: Literal[
        "uncollected", "illegal_dumping", "overflowing_bin", "roadside_litter",
        "burning", "leaking_spill", "blocked_drain", "recurring_dumping",
        "abandoned_electronics", "other", "unknown"
    ]
    amount: Literal[
        "single_item", "very_small", "small", "medium", "large", "very_large", "unknown"
    ]
    condition: Literal[
        "dry", "wet", "leaking", "burning_smoking", "decomposing",
        "damaged_broken", "swollen_battery", "mixed", "unknown"
    ]
    hazards: List[Literal[
        "none_observed", "unknown", "sharps_needles", "broken_glass",
        "rusty_sharp_metal", "medical_material", "chemical_container",
        "chemical_leak", "damaged_battery", "smoke_fire", "strong_fumes",
        "animal_carcass", "pests", "other"
    ]] = Field(min_length=1, max_length=8)
    location_type: Literal[
        "residential", "school_area", "hospital_clinic", "commercial",
        "industrial", "park", "roadside", "open_land", "waterway_drain",
        "collection_point", "other", "unknown"
    ]
    area_landmark: str = Field(min_length=3, max_length=160)
    nearby_sensitive_place: Literal[
        "none", "school", "hospital", "food_market", "playground", "waterway",
        "storm_drain", "busy_road", "residential_homes", "other", "unknown"
    ]
    placement: Literal[
        "roadside", "footpath", "inside_drain", "beside_water", "open_land",
        "alley", "collection_point_bin", "public_area",
        "private_property_visible_from_public", "other", "unknown"
    ]
    duration: Literal[
        "less_than_24h", "one_to_three_days", "four_to_seven_days",
        "one_to_four_weeks", "over_one_month", "unknown"
    ]
    recurrence: Literal[
        "first_occurrence", "happened_before", "repeated_here",
        "continuously_present", "unknown"
    ]
    impacts: List[Literal[
        "none_observed", "unknown", "bad_smell", "pests", "blocked_drainage",
        "water_contamination_concern", "smoke", "road_or_footpath_obstruction",
        "people_children_nearby", "other"
    ]] = Field(min_length=1, max_length=8)
    exposure: Literal[
        "none", "cut_or_puncture", "needlestick", "skin_contact", "eye_contact",
        "inhalation", "ingestion", "burn", "other", "unknown"
    ]
    material_label: str = Field(min_length=2, max_length=160)

    @field_validator("specific_items", "area_landmark", "material_label", mode="before")
    @classmethod
    def clean_text_fields(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_consistency(self):
        def exclusive(values, markers):
            return any(marker in values for marker in markers) and len(values) > 1

        if exclusive(self.waste_types, {"unknown"}):
            raise ValueError("Unknown waste type cannot be combined with identified waste types.")
        if exclusive(self.hazards, {"none_observed", "unknown"}):
            raise ValueError("Hazard 'none observed' or 'unknown' cannot be combined with hazard findings.")
        if exclusive(self.impacts, {"none_observed", "unknown"}):
            raise ValueError("Impact 'none observed' or 'unknown' cannot be combined with reported impacts.")
        if self.condition == "burning_smoking" and "none_observed" in self.hazards:
            raise ValueError("Burning or smoking waste cannot be submitted with 'no hazards observed'.")
        if self.condition == "swollen_battery" and not any(
            item in self.waste_types for item in ("batteries", "e_waste")
        ):
            raise ValueError("A swollen-battery condition requires battery or e-waste to be selected.")
        if self.exposure == "needlestick" and not any(
            item in self.hazards for item in ("sharps_needles", "medical_material")
        ):
            raise ValueError("Needlestick exposure requires a sharps/medical hazard selection.")
        return self


class PublicComplaintRequest(BaseModel):
    text: str = Field(min_length=20, max_length=2000)
    intake: StructuredIntake

    @field_validator("text", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class GuidanceSource(BaseModel):
    source_id: str
    title: str
    issuer: str
    url: str | None = None


class CitizenGuidance(BaseModel):
    risk_level: Literal["routine", "elevated", "high"]
    waste_summary: str
    immediate_precautions: List[str] = Field(default_factory=list)
    disposal_steps: List[str] = Field(default_factory=list)
    if_exposed: List[str] = Field(default_factory=list)
    seek_urgent_help: List[str] = Field(default_factory=list)
    do_not: List[str] = Field(default_factory=list)
    reason: str
    sources: List[GuidanceSource] = Field(default_factory=list)
    evidence_note: str = (
        "Safety guidance is conservative and educational. It does not replace emergency, "
        "medical, poison-control, manufacturer, or local-authority instructions."
    )


class ComplaintRequest(BaseModel):
    text: str = Field(min_length=10, max_length=2000)
    location_context: Optional[str] = Field(default=None, max_length=120)
    clarification_answers: ClarificationAnswers | None = None
    area: str | None = Field(default=None, min_length=3, max_length=120)

    @field_validator("text", "location_context", "area", mode="before")
    @classmethod
    def normalize_input(cls, value):
        return value.strip() if isinstance(value, str) else value


class ImageAnalysisResult(BaseModel):
    visible_waste_types: List[str] = Field(default_factory=list)
    visible_hazards: List[str] = Field(default_factory=list)
    scene_summary: str = ""
    severity_hint: Literal["low", "medium", "high", "unknown"] = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty_notes: List[str] = Field(default_factory=list)
    analyzed: bool = False
    provider: str | None = None
    image_text_conflict: bool = False
    review_reasons: List[str] = Field(default_factory=list)


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
