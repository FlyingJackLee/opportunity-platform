"""Two-layer Filter, spec §14-16. Ordering matters: Layer 1 (cheap, no LLM)
always runs first; Layer 2 (LLM) is only called for items Layer 1 passed."""

from dataclasses import dataclass, field

import structlog

from app.collector.parser import ParsedContent
from app.core.exceptions import LLMError
from app.llm.gateway import LLMGateway
from app.repositories.filter_rule_repository import FilterRules
from app.schemas.filter import FilterRelevanceResult

logger = structlog.get_logger()


@dataclass
class FilterDecision:
    passed: bool
    matched_include: list[str] = field(default_factory=list)
    matched_exclude: list[str] = field(default_factory=list)
    reason: str = ""


def rule_filter(parsed: ParsedContent, rules: FilterRules) -> FilterDecision:
    """spec §15: include_keywords passes if empty OR any keyword
    substring-matches title+content (case-insensitive); exclude_keywords
    rejects if any match, checked first (exclude wins over include)."""
    haystack = f"{parsed.title} {parsed.content}".lower()

    matched_exclude = [kw for kw in rules.exclude_keywords if kw.lower() in haystack]
    if matched_exclude:
        decision = FilterDecision(
            passed=False,
            matched_exclude=matched_exclude,
            reason="matched exclude keyword",
        )
    elif not rules.include_keywords:
        decision = FilterDecision(passed=True, reason="no include keywords configured")
    else:
        matched_include = [kw for kw in rules.include_keywords if kw.lower() in haystack]
        decision = (
            FilterDecision(
                passed=True, matched_include=matched_include, reason="matched include keyword"
            )
            if matched_include
            else FilterDecision(passed=False, reason="no include keyword matched")
        )

    logger.debug(
        "filter_layer1_decision",
        title=parsed.title,
        passed=decision.passed,
        reason=decision.reason,
        matched_include=decision.matched_include,
        matched_exclude=decision.matched_exclude,
    )
    return decision


async def llm_relevance_filter(
    gateway: LLMGateway, *, parsed: ParsedContent, threshold: float
) -> FilterRelevanceResult:
    """spec §16. Raises LLMError on gateway failure -- callers must decide
    fail-open vs fail-closed (app/collector/scheduler.py fails closed, see
    the Phase 3 plan's design judgment #3)."""
    prompt = (
        "这条事件是否可能与政企信息化、数字化、AI、数据、平台建设产生商务机会？\n\n"
        f"【标题】{parsed.title}\n【正文】{parsed.content}"
    )
    try:
        result = await gateway.structured_generate(
            task_type="FILTER_RELEVANCE", prompt=prompt, schema=FilterRelevanceResult
        )
    except Exception as exc:
        raise LLMError(f"filter relevance check failed: {exc}") from exc
    logger.debug(
        "filter_layer2_decision",
        title=parsed.title,
        relevant=result.data.relevant,
        confidence=result.data.confidence,
        threshold=threshold,
        passed=result.data.relevant and result.data.confidence >= threshold,
        reason=result.data.reason,
    )
    return result.data
