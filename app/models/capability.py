import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.knowledge import EMBEDDING_DIMENSION


class Capability(Base, TimestampMixin):
    """spec §35/§80. Own embedding column rather than routing through
    knowledge_chunk -- retrieve_capability's TopK=5 vector search stays a
    direct query against a small (10-20 row) table."""

    __tablename__ = "capability"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    scenarios: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    industries: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    solutions: Mapped[dict | None] = mapped_column(JSON)
    cases: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
