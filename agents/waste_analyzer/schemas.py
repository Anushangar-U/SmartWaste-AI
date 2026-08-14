from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WasteAnalysis(BaseModel):
    waste_types: List[str] = Field(
        description="Types of waste identified in the complaint"
    )

    location: str = Field(
        description="Location where the waste problem occurred"
    )

    duration_days: Optional[int] = Field(
        default=None,
        description="Number of days the waste problem has existed"
    )

    severity: Literal["low", "medium", "high"] = Field(
        description="Estimated severity of the waste complaint"
    )

    issue_type: str = Field(
        description="Category of the waste complaint"
    )

    summary: str = Field(
        description="Short summary of the complaint"
    )