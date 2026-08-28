import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    responsibility: str | None
    topic_tags: list[str] | None
    role_hint: str | None
    source_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class DepartmentCreate(BaseModel):
    organization_id: uuid.UUID
    name: str
    responsibility: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    role_hint: str | None = None
    source_url: str | None = None
    status: str = "ACTIVE"


class DepartmentUpdate(BaseModel):
    name: str | None = None
    responsibility: str | None = None
    topic_tags: list[str] | None = None
    role_hint: str | None = None
    source_url: str | None = None
