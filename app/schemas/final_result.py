from pydantic import BaseModel, Field

from app.schemas.expert import CapabilityResult, Need, OrganizationResult


class DepartmentFinalEntry(BaseModel):
    """One independent Opportunity (ADR-0001) -- a Department with its own
    score/level/confidence (ADR-0002), computed by calculate_score's Send()
    fan-out and joined back in finalize_result."""

    department_id: str
    organization_id: str
    role: str
    related_needs: list[Need] = Field(default_factory=list)
    related_capabilities: list[CapabilityResult] = Field(default_factory=list)
    score: float
    level: str
    confidence: float


class FinalResult(BaseModel):
    """finalize_result's output -- spec §54, minus `stage`. Top-level
    score/level/confidence is a display-only rollup: the full (score, level,
    confidence) triple of whichever department scored highest -- not three
    independently-maxed fields. See CONTEXT.md's FinalResult/Score Level
    entries for the full reasoning."""

    event_id: str
    score: float
    level: str
    confidence: float
    summary: str = ""
    needs: list[Need] = Field(default_factory=list)
    organizations: list[OrganizationResult] = Field(default_factory=list)
    departments: list[DepartmentFinalEntry] = Field(default_factory=list)
    capabilities: list[CapabilityResult] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_action: str = ""
