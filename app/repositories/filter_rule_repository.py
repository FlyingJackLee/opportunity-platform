from dataclasses import dataclass, field

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_filter_rule import EventFilterRule, FilterRuleType

logger = structlog.get_logger()

# spec §15's literal example keyword list
DEFAULT_INCLUDE_KEYWORDS = [
    "AI",
    "人工智能",
    "平台",
    "建设",
    "数据治理",
    "数字化",
    "试点",
    "实施方案",
    "专项资金",
    "采购",
    "招标",
    "升级",
    "改造",
]
DEFAULT_RELEVANCE_THRESHOLD = 0.6


@dataclass
class FilterRules:
    include_keywords: list[str] = field(
        default_factory=lambda: list(DEFAULT_INCLUDE_KEYWORDS)
    )
    exclude_keywords: list[str] = field(default_factory=list)
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD


async def get_filter_rules(session: AsyncSession) -> FilterRules:
    """DB-first (enabled rows), same fallback pattern as
    score_config_repository.get_weights / prompt_repository.get_active_prompt."""
    stmt = select(EventFilterRule).where(EventFilterRule.enabled.is_(True))
    rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        logger.warning("filter_rules_fallback_used")
        return FilterRules()

    include = [r.value for r in rows if r.rule_type == FilterRuleType.INCLUDE_KEYWORD]
    exclude = [r.value for r in rows if r.rule_type == FilterRuleType.EXCLUDE_KEYWORD]
    threshold_rows = [
        r.value for r in rows if r.rule_type == FilterRuleType.RELEVANCE_THRESHOLD
    ]
    threshold = (
        float(threshold_rows[0]) if threshold_rows else DEFAULT_RELEVANCE_THRESHOLD
    )

    return FilterRules(
        include_keywords=include or list(DEFAULT_INCLUDE_KEYWORDS),
        exclude_keywords=exclude,
        relevance_threshold=threshold,
    )
