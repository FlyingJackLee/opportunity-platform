"""spec §12: Parser is decoupled from Collector -- it only knows how to turn
a RawDocument into structured content, keyed by `parser_type` (a column on
collector_source, spec §9), never by which Crawler fetched it.

Kept as the single file spec §95's dev tree shows (not a `parsers/`
subpackage) -- Phase 3 only needs one concrete parser type (GOV_GENERIC) for
a handful of similarly-shaped sources. Split into a subpackage once a second,
meaningfully different site structure actually shows up; this is a
deliberate, revisitable choice, not an oversight."""

import re
from collections.abc import Callable
from datetime import UTC, datetime

from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.collector.crawler import RawDocument
from app.core.exceptions import ParseError

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


class ParsedContent(BaseModel):
    title: str
    content: str
    published_at: datetime | None
    source: str | None
    url: str
    attachments: list[str]


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


def _gov_generic_list_links(html: str, base_url: str) -> list[str]:
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".article-list") or soup
    links = []
    for anchor in container.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        links.append(urljoin(base_url, href))
    return links


def _gov_generic_detail(raw: RawDocument, source_name: str) -> ParsedContent:
    soup = BeautifulSoup(raw.html, "html.parser")

    title_el = soup.select_one("h1") or soup.select_one("title")
    title = title_el.get_text(strip=True) if title_el else ""

    content_el = soup.select_one(".content") or soup.select_one("article")
    content = content_el.get_text(" ", strip=True) if content_el else ""

    if not title or not content:
        raise ParseError(f"could not extract title/content from {raw.url}")

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


PARSER_REGISTRY: dict[str, tuple[Callable, Callable]] = {
    "GOV_GENERIC": (_gov_generic_list_links, _gov_generic_detail),
}


def extract_list_links(html: str, base_url: str, parser_type: str) -> list[str]:
    if parser_type not in PARSER_REGISTRY:
        raise ParseError(f"unknown parser_type={parser_type}")
    list_fn, _ = PARSER_REGISTRY[parser_type]
    return list_fn(html, base_url)


def parse_detail(raw: RawDocument, parser_type: str, source_name: str) -> ParsedContent:
    if parser_type not in PARSER_REGISTRY:
        raise ParseError(f"unknown parser_type={parser_type}")
    _, detail_fn = PARSER_REGISTRY[parser_type]
    return detail_fn(raw, source_name)
