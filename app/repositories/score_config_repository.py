import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score_config import ScoreConfig

logger = structlog.get_logger()

# spec §47
EVENT_RELEVANCE = "event_relevance"
NEED_CLARITY = "need_clarity"
ORGANIZATION_MATCH = "organization_match"
DEPARTMENT_MATCH = "department_match"
COMPANY_CAPABILITY = "company_capability"
PROJECT_SIGNAL = "project_signal"
PROCUREMENT_SIGNAL = "procurement_signal"

DEFAULT_WEIGHTS: dict[str, float] = {
    EVENT_RELEVANCE: 0.15,
    NEED_CLARITY: 0.20,
    ORGANIZATION_MATCH: 0.20,
    DEPARTMENT_MATCH: 0.15,
    COMPANY_CAPABILITY: 0.20,
    PROJECT_SIGNAL: 0.05,
    PROCUREMENT_SIGNAL: 0.05,
}


async def get_weights(session: AsyncSession) -> dict[str, float]:
    """DB-first (enabled rows), falls back to spec §47's literal weights for
    any metric_key with no enabled row."""
    stmt = select(ScoreConfig).where(ScoreConfig.enabled.is_(True))
    rows = (await session.execute(stmt)).scalars().all()
    weights = dict(DEFAULT_WEIGHTS)
    if not rows:
        logger.warning("score_config_fallback_used")
    for row in rows:
        weights[row.metric_key] = row.weight
    return weights
