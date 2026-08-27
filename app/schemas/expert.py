from enum import StrEnum

from pydantic import BaseModel, Field


class NeedMaturity(StrEnum):
    CONCEPT = "CONCEPT"
    POTENTIAL = "POTENTIAL"
    EXPLICIT = "EXPLICIT"
    PROJECT = "PROJECT"
    PROCUREMENT = "PROCUREMENT"


class Need(BaseModel):
    name: str
    confidence: float
    maturity: NeedMaturity


class CapabilityResult(BaseModel):
    capability: str
    score: float


class OrganizationResult(BaseModel):
    organization_id: str
    score: float


class DepartmentResult(BaseModel):
    """spec §43's departments[] entry, extended with two fields not in the
    literal spec JSON -- see the Phase 2 plan's design-judgment #1 and #2:

    - organization_id: without it, a department_id="UNKNOWN" branch (spec
      §72's sanctioned fallback) has nothing to attribute Organization Match
      scoring to.
    - related_capabilities: mirrors related_needs, so Company Capability
      scoring (20% weight, spec §47) is genuinely independent per department
      rather than every department sharing one event-level average --
      confirmed with the user, this is the whole point of ADR-0002.
    """

    department_id: str
    organization_id: str
    role: str
    confidence: float
    related_needs: list[Need] = Field(default_factory=list)
    related_capabilities: list[CapabilityResult] = Field(default_factory=list)


class ExpertResult(BaseModel):
    """expert_judge's raw structured output -- spec §43. No `stage` field:
    "商机阶段" was dropped during design (see CONTEXT.md's Need Maturity entry)."""

    needs: list[Need] = Field(default_factory=list)
    organizations: list[OrganizationResult] = Field(default_factory=list)
    departments: list[DepartmentResult] = Field(default_factory=list)
    capabilities: list[CapabilityResult] = Field(default_factory=list)
    reason: str = ""
    risks: list[str] = Field(default_factory=list)
    recommended_action: str = ""
