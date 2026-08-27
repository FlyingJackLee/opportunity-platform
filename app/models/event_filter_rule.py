import uuid
from enum import StrEnum

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FilterRuleType(StrEnum):
    INCLUDE_KEYWORD = "INCLUDE_KEYWORD"
    EXCLUDE_KEYWORD = "EXCLUDE_KEYWORD"
    RELEVANCE_THRESHOLD = "RELEVANCE_THRESHOLD"


class EventFilterRule(Base, TimestampMixin):
    """spec §15. Not in spec §80's 10-core-table list -- an 11th table added
    to follow the DB-first/hardcoded-fallback convention already established
    by prompt_template/score_config, since operators are expected to tune
    these keywords during the trial run (spec §101) without a redeploy."""

    __tablename__ = "event_filter_rule"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_type: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
