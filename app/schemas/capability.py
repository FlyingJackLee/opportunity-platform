import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CapabilityRead(BaseModel):
    """embedding deliberately omitted -- server-computed, see
    app/knowledge/ingestion.py."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    scenarios: list[str] | None
    industries: list[str] | None
    solutions: dict | None
    cases: dict | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CapabilityCreate(BaseModel):
    name: str
    scenarios: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    solutions: dict | None = None
    cases: dict | None = None
    description: str | None = None
    status: str = "ACTIVE"


class CapabilityUpdate(BaseModel):
    name: str | None = None
    scenarios: list[str] | None = None
    industries: list[str] | None = None
    solutions: dict | None = None
    cases: dict | None = None
    description: str | None = None
