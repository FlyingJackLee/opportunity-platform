import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.vocabulary import SourceType


class CollectorSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    base_url: str | None
    list_url: str
    enabled: bool
    schedule: str
    parser_type: str
    industry_tags: list[str] | None
    region_tags: list[str] | None
    priority: int
    created_at: datetime
    updated_at: datetime


class CollectorSourceCreate(BaseModel):
    name: str
    source_type: str
    base_url: str | None = None
    list_url: str
    enabled: bool = True
    schedule: str
    parser_type: str
    industry_tags: list[str] | None = None
    region_tags: list[str] | None = None
    priority: int = 0

    @field_validator("source_type")
    @classmethod
    def source_type_in_vocabulary(cls, v: str) -> str:
        if v not in SourceType:
            raise ValueError(f"'{v}' is not in the controlled SourceType vocabulary")
        return v


class CollectorSourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    base_url: str | None = None
    list_url: str | None = None
    schedule: str | None = None
    parser_type: str | None = None
    industry_tags: list[str] | None = None
    region_tags: list[str] | None = None
    priority: int | None = None

    @field_validator("source_type")
    @classmethod
    def source_type_in_vocabulary(cls, v: str | None) -> str | None:
        if v is not None and v not in SourceType:
            raise ValueError(f"'{v}' is not in the controlled SourceType vocabulary")
        return v


class CollectorRunResponse(BaseModel):
    source_id: str
    fetched: int
    created: int
    deduped: int
    filtered_out: int
    triggered_analysis: int
    errors: list[str]
