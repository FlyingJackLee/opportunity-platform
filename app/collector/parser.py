"""spec §12: Parser is decoupled from Collector -- it only knows how to turn
a RawDocument into structured content, keyed by `parser_type` (a column on
collector_source, spec §9), never by which Crawler fetched it.

Kept as the single file spec §95's dev tree shows (not a `parsers/`
subpackage) -- Phase 3 only needs one concrete parser type (GOV_GENERIC) for
a handful of similarly-shaped sources. Split into a subpackage once a second,
meaningfully different site structure actually shows up; this is a
deliberate, revisitable choice, not an oversight.

CSS-selector extraction (GOV_GENERIC) stays the first, free, deterministic
attempt. Real-world sites (verified against 13 government + 4 news sources
while onboarding real collector_source rows) vary enough in HTML structure
that CSS-only coverage is poor -- an LLM fallback (_llm_list_links/
_llm_detail) kicks in only when the CSS attempt yields nothing, mirroring
the Filter module's own cheap-first/LLM-second layering
(app/collector/filter.py). It cannot help when the content genuinely isn't
in the fetched HTML (JS-rendered pages) -- that's a Crawler-level gap
(see app/collector/crawler.py's Crawler Protocol), not a parsing one."""

import re
from collections.abc import Callable
from datetime import UTC, datetime

import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.collector.crawler import RawDocument
from app.core.exceptions import ParseError
from app.llm.gateway import LLMGateway

logger = structlog.get_logger()

_DATE_PATTERNS = [
    (
        re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
        lambda m: (int(m[1]), int(m[2]), int(m[3])),
    ),
    (
        re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
        lambda m: (int(m[1]), int(m[2]), int(m[3])),
    ),
]

_LLM_HTML_MAX_CHARS = 40_000


class ParsedContent(BaseModel):
    title: str
    content: str
    published_at: datetime | None
    source: str | None
    url: str
    attachments: list[str]


class LLMFallbackBudget:
    """Caps LLM parse-fallback calls per collection cycle (shared across one
    run_collection_cycle call, see app/collector/scheduler.py). A source
    whose CSS extraction never matches would otherwise retry the LLM path
    for every item on every scheduled run forever -- silently spending money
    on a source that needs an operator's attention (wrong parser_type, needs
    a JS-rendering crawler, dead URL), not infinite retries."""

    def __init__(self, max_calls: int) -> None:
        self.remaining = max_calls

    def consume(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True


class _ExtractedLinks(BaseModel):
    links: list[str]


class _ExtractedArticle(BaseModel):
    title: str
    content: str
    published_at: str = ""


def _parse_date(text: str) -> datetime | None:
    for pattern, extract in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            year, month, day = extract(match)
            try:
                return datetime(year, month, day, tzinfo=UTC)
            except ValueError:
                continue
    return None


def _clean_html_for_llm(html: str, *, max_chars: int = _LLM_HTML_MAX_CHARS) -> str:
    """Strips script/style noise (the bulk of most CMS pages' byte weight)
    before handing HTML to the LLM -- keeps prompts smaller/cheaper without
    losing the tag structure the model needs (hrefs, headings)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return str(soup)[:max_chars]


def _gov_generic_list_links(html: str, base_url: str) -> list[str]:
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".article-list")
    if container is None:
        # No silent whole-page fallback: that used to scoop up nav/breadcrumb
        # links (real failure mode hit onboarding mohurd.gov.cn) instead of
        # actual article links. An empty result here is what triggers the
        # LLM fallback in extract_list_links below.
        return []
    links = []
    for anchor in container.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        links.append(urljoin(base_url, href))
    return links


def _gov_generic_detail(raw: RawDocument, source_name: str) -> ParsedContent | None:
    soup = BeautifulSoup(raw.html, "html.parser")

    title_el = soup.select_one("h1") or soup.select_one("title")
    title = title_el.get_text(strip=True) if title_el else ""

    content_el = soup.select_one(".content") or soup.select_one("article")
    content = content_el.get_text(" ", strip=True) if content_el else ""

    if not title or not content:
        return None

    date_el = soup.select_one(".date")
    published_at = (
        _parse_date(date_el.get_text(strip=True)) if date_el else _parse_date(raw.html)
    )

    attachments = [
        a["href"]
        for a in soup.select(".attachments a[href]")
        if a.get("href", "").strip()
    ]

    return ParsedContent(
        title=title,
        content=content,
        published_at=published_at,
        source=source_name,
        url=raw.url,
        attachments=attachments,
    )


async def _llm_list_links(html: str, base_url: str, gateway: LLMGateway) -> list[str]:
    from urllib.parse import urljoin

    cleaned = _clean_html_for_llm(html)
    logger.debug(
        "llm_list_links_call", base_url=base_url, prompt_chars=len(cleaned)
    )
    prompt = (
        "这是一个政府/媒体网站的公告或新闻列表页的 HTML。找出页面里指向具体一篇公告/新闻"
        "详情页的链接（不是导航栏、面包屑、页眉页脚、友情链接这些站点通用链接）。"
        "href 可以是相对路径。\n\n"
        f"{cleaned}"
    )
    result = await gateway.structured_generate(
        task_type="PARSE_LIST_LINKS", prompt=prompt, schema=_ExtractedLinks
    )
    links = [urljoin(base_url, href) for href in result.data.links if href.strip()]
    logger.debug("llm_list_links_result", base_url=base_url, link_count=len(links))
    return links


async def _llm_detail(raw: RawDocument, source_name: str, gateway: LLMGateway) -> ParsedContent | None:
    cleaned = _clean_html_for_llm(raw.html)
    logger.debug("llm_detail_call", url=raw.url, prompt_chars=len(cleaned))
    prompt = (
        "这是一篇公告/新闻详情页的 HTML。提取它的标题、正文（去掉导航/广告/相关推荐等"
        "无关内容，只要正文本身）、发布日期（找不到就留空）。\n\n"
        f"{cleaned}"
    )
    result = await gateway.structured_generate(
        task_type="PARSE_DETAIL", prompt=prompt, schema=_ExtractedArticle
    )
    article = result.data
    if not article.title or not article.content:
        logger.debug("llm_detail_result_empty", url=raw.url)
        return None
    logger.debug(
        "llm_detail_result_ok",
        url=raw.url,
        title=article.title,
        content_chars=len(article.content),
    )
    return ParsedContent(
        title=article.title,
        content=article.content,
        published_at=_parse_date(article.published_at) if article.published_at else None,
        source=source_name,
        url=raw.url,
        attachments=[],
    )


PARSER_REGISTRY: dict[str, tuple[Callable, Callable]] = {
    "GOV_GENERIC": (_gov_generic_list_links, _gov_generic_detail),
}


async def extract_list_links(
    html: str,
    base_url: str,
    parser_type: str,
    *,
    gateway: LLMGateway | None = None,
    budget: LLMFallbackBudget | None = None,
) -> list[str]:
    if parser_type not in PARSER_REGISTRY:
        raise ParseError(f"unknown parser_type={parser_type}")
    list_fn, _ = PARSER_REGISTRY[parser_type]
    links = list_fn(html, base_url)
    logger.debug("css_list_links_result", base_url=base_url, link_count=len(links))
    if links:
        return links
    if gateway is None:
        logger.debug("llm_list_links_skipped", base_url=base_url, reason="no_gateway")
        return links
    if budget is None or not budget.consume():
        logger.debug("llm_list_links_skipped", base_url=base_url, reason="budget_exhausted")
        return links
    return await _llm_list_links(html, base_url, gateway)


async def parse_detail(
    raw: RawDocument,
    parser_type: str,
    source_name: str,
    *,
    gateway: LLMGateway | None = None,
    budget: LLMFallbackBudget | None = None,
) -> ParsedContent:
    if parser_type not in PARSER_REGISTRY:
        raise ParseError(f"unknown parser_type={parser_type}")
    _, detail_fn = PARSER_REGISTRY[parser_type]
    parsed = detail_fn(raw, source_name)
    logger.debug("css_detail_result", url=raw.url, ok=parsed is not None)
    if parsed is None:
        if gateway is None:
            logger.debug("llm_detail_skipped", url=raw.url, reason="no_gateway")
        elif budget is None or not budget.consume():
            logger.debug("llm_detail_skipped", url=raw.url, reason="budget_exhausted")
        else:
            parsed = await _llm_detail(raw, source_name, gateway)
    if parsed is None:
        raise ParseError(f"could not extract title/content from {raw.url}")
    return parsed
