import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ExpertRun(Base, TimestampMixin):
    """spec §55, prompt-version fields per §79 (3 columns, not the single
    `prompt_version` §55 mentions -- §79 is more specific)."""

    __tablename__ = "expert_run"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event.id"), index=True
    )

    graph_version: Mapped[str] = mapped_column(String(50))
    model_version: Mapped[str | None] = mapped_column(String(100))
    event_prompt_version: Mapped[str | None] = mapped_column(String(50))
    judge_prompt_version: Mapped[str | None] = mapped_column(String(50))
    review_prompt_version: Mapped[str | None] = mapped_column(String(50))

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="RUNNING")

    score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str | None] = mapped_column(String(10))
    confidence: Mapped[float | None] = mapped_column(Float)

    result_json: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
