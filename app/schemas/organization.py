import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    short_name: str | None
    region: str | None
    organization_type: str | None
    parent_id: uuid.UUID | None
    description: str | None
    source_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str
    short_name: str | None = None
    region: str | None = None
    organization_type: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = None
    source_url: str | None = None
    status: str = "ACTIVE"


class OrganizationUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    region: str | None = None
    organization_type: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = None
    source_url: str | None = None
