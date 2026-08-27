import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class CollectorRunResponse(BaseModel):
    source_id: str
    fetched: int
    created: int
    deduped: int
    filtered_out: int
    triggered_analysis: int
    errors: list[str]
