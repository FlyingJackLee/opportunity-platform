from datetime import UTC, datetime

import pytest

from app.collector.crawler import RawDocument
from app.collector.parser import (
    LLMFallbackBudget,
    _ExtractedArticle,
    _ExtractedLinks,
    extract_list_links,
    parse_detail,
)
from app.core.exceptions import ParseError
from app.llm.providers.stub import StubLLMGateway

LIST_HTML = """
<div class="article-list">
  <a href="/a.html">Item A</a>
  <a href="/b.html">Item B</a>
</div>
"""

# No .article-list container -- this is the real failure mode hit onboarding
# mohurd.gov.cn: a CMS page whose article list is JS-rendered/differently
# structured, leaving only unrelated links (nav here) in the static HTML.
NO_CONTAINER_HTML = """
<nav><a href="/index.html">首页</a><a href="/news/index.html">新闻</a></nav>
"""

DETAIL_HTML = """
<html><body>
<h1>测试标题</h1>
<span class="date">2026-08-20</span>
<div class="content">测试正文内容</div>
<div class="attachments"><a href="/f.pdf">附件</a></div>
</body></html>
"""

INCOMPLETE_HTML = "<html><body><p>no title or content div here</p></body></html>"


async def test_extract_list_links_resolves_relative_urls() -> None:
    links = await extract_list_links(LIST_HTML, "https://example.invalid", "GOV_GENERIC")
    assert links == ["https://example.invalid/a.html", "https://example.invalid/b.html"]


async def test_extract_list_links_unknown_parser_type_raises() -> None:
    with pytest.raises(ParseError):
        await extract_list_links(LIST_HTML, "https://example.invalid", "NOPE")


async def test_parse_detail_extracts_fields() -> None:
    raw = RawDocument(
        url="https://example.invalid/a.html",
        html=DETAIL_HTML,
        fetched_at=datetime.now(UTC),
    )
    parsed = await parse_detail(raw, "GOV_GENERIC", "测试来源")

    assert parsed.title == "测试标题"
    assert parsed.content == "测试正文内容"
    assert parsed.published_at == datetime(2026, 8, 20, tzinfo=UTC)
    assert parsed.source == "测试来源"
    assert parsed.attachments == ["/f.pdf"]


async def test_parse_detail_missing_title_or_content_raises() -> None:
    raw = RawDocument(
        url="https://example.invalid/x.html",
        html=INCOMPLETE_HTML,
        fetched_at=datetime.now(UTC),
    )
    with pytest.raises(ParseError):
        await parse_detail(raw, "GOV_GENERIC", "测试来源")


async def test_extract_list_links_no_container_returns_empty_without_gateway() -> None:
    """No LLM configured (gateway=None, the default) -- CSS-only behavior,
    no whole-page nav-link fallback."""
    links = await extract_list_links(NO_CONTAINER_HTML, "https://example.invalid", "GOV_GENERIC")
    assert links == []


async def test_extract_list_links_falls_back_to_llm_when_css_finds_nothing() -> None:
    gateway = StubLLMGateway(
        fixture_overrides={
            "PARSE_LIST_LINKS": _ExtractedLinks(links=["/real-article-1.html"])
        }
    )
    budget = LLMFallbackBudget(5)
    links = await extract_list_links(
        NO_CONTAINER_HTML, "https://example.invalid", "GOV_GENERIC", gateway=gateway, budget=budget
    )
    assert links == ["https://example.invalid/real-article-1.html"]
    assert budget.remaining == 4


async def test_extract_list_links_does_not_call_llm_when_budget_exhausted() -> None:
    gateway = StubLLMGateway(
        fixture_overrides={"PARSE_LIST_LINKS": _ExtractedLinks(links=["/should-not-be-used.html"])}
    )
    budget = LLMFallbackBudget(0)
    links = await extract_list_links(
        NO_CONTAINER_HTML, "https://example.invalid", "GOV_GENERIC", gateway=gateway, budget=budget
    )
    assert links == []


async def test_parse_detail_falls_back_to_llm_when_css_selectors_miss() -> None:
    raw = RawDocument(
        url="https://example.invalid/x.html",
        html=INCOMPLETE_HTML,
        fetched_at=datetime.now(UTC),
    )
    gateway = StubLLMGateway(
        fixture_overrides={
            "PARSE_DETAIL": _ExtractedArticle(
                title="LLM 抽取的标题", content="LLM 抽取的正文", published_at="2026-08-20"
            )
        }
    )
    budget = LLMFallbackBudget(5)
    parsed = await parse_detail(raw, "GOV_GENERIC", "测试来源", gateway=gateway, budget=budget)

    assert parsed.title == "LLM 抽取的标题"
    assert parsed.content == "LLM 抽取的正文"
    assert parsed.published_at == datetime(2026, 8, 20, tzinfo=UTC)
    assert budget.remaining == 4


async def test_parse_detail_budget_exhausted_still_raises() -> None:
    raw = RawDocument(
        url="https://example.invalid/x.html",
        html=INCOMPLETE_HTML,
        fetched_at=datetime.now(UTC),
    )
    gateway = StubLLMGateway(
        fixture_overrides={
            "PARSE_DETAIL": _ExtractedArticle(title="不该被用到", content="不该被用到")
        }
    )
    budget = LLMFallbackBudget(0)
    with pytest.raises(ParseError):
        await parse_detail(raw, "GOV_GENERIC", "测试来源", gateway=gateway, budget=budget)
