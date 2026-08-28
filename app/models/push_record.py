import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PushRecordStatus(StrEnum):
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RecipientType(StrEnum):
    DEPARTMENT_OWNER = "DEPARTMENT_OWNER"
    ORGANIZATION_OWNER = "ORGANIZATION_OWNER"
    PUBLIC_GROUP = "PUBLIC_GROUP"
    NONE = "NONE"


class PushRecord(Base, TimestampMixin):
    """spec §66. One row per department branch (ADR-0001/0002's Opportunity
    granularity) -- including SKIPPED (should_push=False) branches, so Trace
    (spec §106) covers every Opportunity outcome, not just successful sends."""

    __tablename__ = "push_record"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event.id"), index=True
    )
    expert_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expert_run.id"), index=True
    )

    # str, not FK: must tolerate the "UNKNOWN" sentinel (ADR-0002)
    department_id: Mapped[str] = mapped_column(String(64))
    organization_id: Mapped[str] = mapped_column(String(64))

    channel: Mapped[str | None] = mapped_column(String(30))
    recipient_type: Mapped[str] = mapped_column(String(30))
    recipient_id: Mapped[str | None] = mapped_column(String(100))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_owner.id")
    )

    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
