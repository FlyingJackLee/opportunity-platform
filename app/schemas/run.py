from typing import Any

from pydantic import BaseModel


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    values: dict[str, Any] | None = None
    error: str | None = None
