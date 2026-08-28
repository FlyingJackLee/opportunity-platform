import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RunSummary(BaseModel):
    """Lightweight per-run row for an event's run history -- the full
    values/push payload stays on GET /runs/{run_id} (RunStatusResponse
    below), fetched only when a specific run is opened."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    score: float | None
    level: str | None
    confidence: float | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None


class PushSummary(BaseModel):
    """spec §106 Trace: "为什么推给某人"/"是否发送成功", surfaced per department
    branch."""

    department_id: str
    organization_id: str
    recipient_type: str
    recipient_id: str | None
    status: str
    sent_at: datetime | None
    error: str | None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    values: dict[str, Any] | None = None
    error: str | None = None
    push: list[PushSummary] | None = None
