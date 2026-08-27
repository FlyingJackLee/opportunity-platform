"""spec §11. Only StaticCrawler is implemented in Phase 3 -- spec §98's
acceptance scope for this phase is literally just Static Crawler, and "非必要
不使用浏览器爬虫" (§11) argues against adding Playwright (DynamicCrawler)
speculatively. RSSCollector/APICollector are similarly deferred. `Crawler` is
a Protocol so any of those can be added later without touching call sites --
Parser (app/collector/parser.py) owns all HTML-structure knowledge, Crawler
only fetches raw documents (spec §12: Parser decoupled from Collector)."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog
from pydantic import BaseModel

from app.core.exceptions import CollectError

USER_AGENT = "OpportunityPlatformBot/0.1 (+collector; respects robots.txt)"
MIN_REQUEST_INTERVAL_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 10.0

logger = structlog.get_logger()


class RawDocument(BaseModel):
    url: str
    html: str
    fetched_at: datetime


class Crawler(Protocol):
    async def fetch(self, url: str) -> RawDocument: ...


class StaticCrawler:
    """httpx-based fetch for statically-rendered pages (spec §11's
    StaticCrawler: httpx + BeautifulSoup -- BeautifulSoup lives in parser.py).
    Checks robots.txt per host (cached), enforces a minimum delay between
    requests to the same host, raises CollectError on unrecoverable failures
    -- this is where spec §91's compliance requirements are enforced."""

    def __init__(
        self, *, min_interval_seconds: float = MIN_REQUEST_INTERVAL_SECONDS
    ) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        self._min_interval = min_interval_seconds
        self._robots_cache: dict[str, RobotFileParser] = {}
        self._last_request_at: dict[str, float] = {}

    async def _get_robots(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        host = parsed.netloc
        if host not in self._robots_cache:
            parser = RobotFileParser()
            robots_url = f"{parsed.scheme}://{host}/robots.txt"
            try:
                response = await self._client.get(robots_url)
                parser.parse(
                    response.text.splitlines() if response.status_code == 200 else []
                )
            except httpx.HTTPError:
                parser.parse([])  # unreachable robots.txt -> treat as allow-all
            self._robots_cache[host] = parser
        return self._robots_cache[host]

    async def fetch(self, url: str) -> RawDocument:
        robots = await self._get_robots(url)
        if not robots.can_fetch(USER_AGENT, url):
            raise CollectError(f"robots.txt disallows fetching {url}")

        host = urlparse(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)

        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CollectError(f"failed to fetch {url}: {exc}") from exc
        finally:
            self._last_request_at[host] = time.monotonic()

        return RawDocument(url=url, html=response.text, fetched_at=datetime.now(UTC))

    async def aclose(self) -> None:
        await self._client.aclose()
