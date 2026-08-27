import pytest

from app.collector.filter import llm_relevance_filter, rule_filter
from app.collector.parser import ParsedContent
from app.llm.providers.stub import StubLLMGateway
from app.repositories.filter_rule_repository import FilterRules
from app.schemas.filter import FilterRelevanceResult


def _parsed(title: str, content: str) -> ParsedContent:
    return ParsedContent(
        title=title,
        content=content,
        published_at=None,
        source=None,
        url="https://x.invalid",
        attachments=[],
    )


@pytest.mark.parametrize(
    ("title", "content", "rules", "expected_passed"),
    [
        ("市住建委关于数字化建设的通知", "推动平台建设", FilterRules(), True),
        ("市图书馆读书活动通知", "举办读书分享会", FilterRules(), False),
        ("测试事件", "任意内容", FilterRules(include_keywords=[]), True),
        (
            "包含数字化的标题",
            "但也提到了裁员",
            FilterRules(exclude_keywords=["裁员"]),
            False,
        ),
    ],
)
def test_rule_filter_include_exclude(title, content, rules, expected_passed) -> None:
    decision = rule_filter(_parsed(title, content), rules)
    assert decision.passed is expected_passed


def test_rule_filter_exclude_wins_over_include() -> None:
    rules = FilterRules(include_keywords=["数字化"], exclude_keywords=["裁员"])
    decision = rule_filter(_parsed("数字化转型但公司裁员", "内容"), rules)
    assert decision.passed is False


async def test_llm_relevance_filter_default_stub_passes() -> None:
    gateway = StubLLMGateway()
    result = await llm_relevance_filter(
        gateway, parsed=_parsed("t", "c"), threshold=0.6
    )
    assert result.relevant is True
    assert result.confidence >= 0.6


async def test_llm_relevance_filter_can_be_overridden_to_reject() -> None:
    gateway = StubLLMGateway(
        fixture_overrides={
            "FILTER_RELEVANCE": FilterRelevanceResult(
                relevant=False, confidence=0.3, reason="不相关"
            )
        }
    )
    result = await llm_relevance_filter(
        gateway, parsed=_parsed("t", "c"), threshold=0.6
    )
    assert result.relevant is False
    assert result.confidence < 0.6
