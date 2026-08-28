import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.vocabulary import OrganizationType


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

    @field_validator("organization_type")
    @classmethod
    def organization_type_in_vocabulary(cls, v: str | None) -> str | None:
        if v is not None and v not in OrganizationType:
            raise ValueError(f"'{v}' is not in the controlled OrganizationType vocabulary")
        return v


class OrganizationUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    region: str | None = None
    organization_type: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = None
    source_url: str | None = None

    @field_validator("organization_type")
    @classmethod
    def organization_type_in_vocabulary(cls, v: str | None) -> str | None:
        if v is not None and v not in OrganizationType:
            raise ValueError(f"'{v}' is not in the controlled OrganizationType vocabulary")
        return v
