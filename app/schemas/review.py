from pydantic import BaseModel, Field


class ReviewResult(BaseModel):
    """mini_review's structured output -- spec §52."""

    approved: bool
    adjustments: list[str] = Field(default_factory=list)
    risk_note: str = ""
