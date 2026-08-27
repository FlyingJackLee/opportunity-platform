import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

EMBEDDING_DIMENSION = 1536


class KnowledgeChunk(Base, TimestampMixin):
    """spec §37. Phase 2 only writes/queries knowledge_type='INDUSTRY'."""

    __tablename__ = "knowledge_chunk"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    knowledge_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(50))
    region: Mapped[str | None] = mapped_column(String(50))
    topic: Mapped[str | None] = mapped_column(String(255))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
