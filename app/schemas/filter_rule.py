import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.event_filter_rule import FilterRuleType


class EventFilterRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_type: str
    value: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class EventFilterRuleCreate(BaseModel):
    rule_type: str
    value: str
    enabled: bool = True

    @field_validator("rule_type")
    @classmethod
    def rule_type_in_vocabulary(cls, v: str) -> str:
        if v not in FilterRuleType:
            raise ValueError(f"'{v}' is not in the controlled FilterRuleType vocabulary")
        return v


class EventFilterRuleUpdate(BaseModel):
    value: str | None = None
