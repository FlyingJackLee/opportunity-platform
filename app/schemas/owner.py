import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerOwnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    department_id: uuid.UUID | None
    owner_name: str
    owner_user_id: str | None
    dingtalk_user_id: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CustomerOwnerCreate(BaseModel):
    organization_id: uuid.UUID
    department_id: uuid.UUID | None = None
    owner_name: str
    owner_user_id: str | None = None
    dingtalk_user_id: str | None = None
    enabled: bool = True
