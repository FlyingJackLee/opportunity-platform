from pydantic import BaseModel


class FilterRelevanceResult(BaseModel):
    """Filter Layer 2's structured output -- spec §16's exact shape."""

    relevant: bool
    confidence: float
    reason: str = ""
