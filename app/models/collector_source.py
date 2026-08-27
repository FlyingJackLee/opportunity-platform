import uuid

from sqlalchemy import ARRAY, Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CollectorSource(Base, TimestampMixin):
    """spec §9. `source_type` here is a site-category vocabulary
    (GOV_WEB/tender site/...) -- a different thing from Event.source_type
    (PUBLIC_WEB/MANUAL, the ingestion channel). See CONTEXT.md."""

    __tablename__ = "collector_source"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))
    base_url: Mapped[str | None] = mapped_column(String(2048))
    list_url: Mapped[str] = mapped_column(String(2048))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule: Mapped[str] = mapped_column(String(100))
    parser_type: Mapped[str] = mapped_column(String(50))
    industry_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    region_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    priority: Mapped[int] = mapped_column(Integer, default=0)
