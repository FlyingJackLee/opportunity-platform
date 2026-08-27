from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """spec §26 only shows one example value ("POLICY") and never enumerates
    the full set -- this list is inferred, not spec-literal."""

    POLICY = "POLICY"
    TENDER = "TENDER"
    NEWS = "NEWS"
    PROJECT_APPROVAL = "PROJECT_APPROVAL"
    OTHER = "OTHER"


class SignalLevel(StrEnum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Signals(BaseModel):
    project_signal: SignalLevel = SignalLevel.UNKNOWN
    budget_signal: SignalLevel = SignalLevel.UNKNOWN
    procurement_signal: SignalLevel = SignalLevel.UNKNOWN


class EventAnalysis(BaseModel):
    """analyze_event's structured output -- spec §26. Understands the event;
    must not make business judgments (spec §27's constraints belong in the
    prompt text, not enforced here)."""

    event_type: EventType
    region: str
    industry: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    signals: Signals = Field(default_factory=Signals)
