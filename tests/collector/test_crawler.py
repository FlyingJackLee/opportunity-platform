import pytest

from app.collector.crawler import StaticCrawler
from app.core.exceptions import CollectError


async def test_static_crawler_fetches_real_page(local_fixture_server) -> None:
    crawler = StaticCrawler()
    try:
        doc = await crawler.fetch(f"{local_fixture_server}/list.html")
        assert "article-list" in doc.html
        assert doc.url == f"{local_fixture_server}/list.html"
    finally:
        await crawler.aclose()


async def test_static_crawler_raises_collect_error_on_404(local_fixture_server) -> None:
    crawler = StaticCrawler()
    try:
        with pytest.raises(CollectError):
            await crawler.fetch(f"{local_fixture_server}/does-not-exist.html")
    finally:
        await crawler.aclose()


async def test_static_crawler_raises_collect_error_on_connection_refused() -> None:
    crawler = StaticCrawler()
    try:
        with pytest.raises(CollectError):
            await crawler.fetch("http://127.0.0.1:1/unreachable")
    finally:
        await crawler.aclose()
