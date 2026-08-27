import hashlib
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EventStatus(StrEnum):
    """Event lifecycle states, spec §18."""

    NEW = "NEW"
    FILTERED_OUT = "FILTERED_OUT"
    WAITING_ANALYSIS = "WAITING_ANALYSIS"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    PUSHED = "PUSHED"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


def compute_content_hash(content: str) -> str:
    """Normalized content hash for Collector dedup (spec §13). Computed even for
    manually-created events so Phase 3's dedup logic works without a backfill."""
    normalized = " ".join(content.split()).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class Event(Base, TimestampMixin):
    __tablename__ = "event"
    __table_args__ = (
        Index("ix_event_status", "status"),
        Index("ix_event_content_hash", "content_hash"),
        Index("ix_event_external_id", "external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str | None] = mapped_column(String(255))

    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)

    source_type: Mapped[str] = mapped_column(String(50))
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(2048))

    published_at: Mapped[datetime | None]
    collected_at: Mapped[datetime | None]

    region: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[str] = mapped_column(String(30), default=EventStatus.NEW)

    content_hash: Mapped[str | None] = mapped_column(String(64))
    filter_score: Mapped[float | None] = mapped_column(Float)
