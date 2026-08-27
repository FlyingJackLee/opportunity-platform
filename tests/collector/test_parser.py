from datetime import UTC, datetime

import pytest

from app.collector.crawler import RawDocument
from app.collector.parser import extract_list_links, parse_detail
from app.core.exceptions import ParseError

LIST_HTML = """
<div class="article-list">
  <a href="/a.html">Item A</a>
  <a href="/b.html">Item B</a>
</div>
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


def test_extract_list_links_resolves_relative_urls() -> None:
    links = extract_list_links(LIST_HTML, "https://example.invalid", "GOV_GENERIC")
    assert links == ["https://example.invalid/a.html", "https://example.invalid/b.html"]


def test_extract_list_links_unknown_parser_type_raises() -> None:
    with pytest.raises(ParseError):
        extract_list_links(LIST_HTML, "https://example.invalid", "NOPE")


def test_parse_detail_extracts_fields() -> None:
    raw = RawDocument(
        url="https://example.invalid/a.html",
        html=DETAIL_HTML,
        fetched_at=datetime.now(UTC),
    )
    parsed = parse_detail(raw, "GOV_GENERIC", "测试来源")

    assert parsed.title == "测试标题"
    assert parsed.content == "测试正文内容"
    assert parsed.published_at == datetime(2026, 8, 20, tzinfo=UTC)
    assert parsed.source == "测试来源"
    assert parsed.attachments == ["/f.pdf"]


def test_parse_detail_missing_title_or_content_raises() -> None:
    raw = RawDocument(
        url="https://example.invalid/x.html",
        html=INCOMPLETE_HTML,
        fetched_at=datetime.now(UTC),
    )
    with pytest.raises(ParseError):
        parse_detail(raw, "GOV_GENERIC", "测试来源")
