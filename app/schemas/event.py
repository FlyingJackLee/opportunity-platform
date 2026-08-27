import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.vocabulary import Industry, Region


class EventCreate(BaseModel):
    title: str
    content: str
    source_type: str = "MANUAL"
    source_name: str | None = None
    source_url: str | None = None
    region: str | None = None
    industry: str | None = None

    @field_validator("region")
    @classmethod
    def region_in_vocabulary(cls, v: str | None) -> str | None:
        if v is not None and v not in Region:
            raise ValueError(f"'{v}' is not in the controlled Region vocabulary")
        return v

    @field_validator("industry")
    @classmethod
    def industry_in_vocabulary(cls, v: str | None) -> str | None:
        if v is not None and v not in Industry:
            raise ValueError(f"'{v}' is not in the controlled Industry vocabulary")
        return v


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str | None
    title: str
    content: str
    source_type: str
    source_name: str | None
    source_url: str | None
    published_at: datetime | None
    collected_at: datetime | None
    region: str | None
    industry: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class EventCreateResponse(BaseModel):
    event_id: uuid.UUID
    run_id: str
    status: str = "PROCESSING"
