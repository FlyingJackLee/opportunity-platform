"""Per-source collection cycle orchestration + APScheduler wiring, spec §10.
Kept in one file per spec §95's exact `app/collector/{scheduler,crawler,
parser,dedup,filter}.py` layout -- this is where Collector's own
"pipeline" lives, there's no separate pipeline.py."""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.collector.crawler import Crawler
from app.collector.dedup import find_duplicate, url_already_collected
from app.collector.filter import llm_relevance_filter, rule_filter
from app.collector.parser import LLMFallbackBudget, extract_list_links, parse_detail
from app.core.config import get_settings
from app.core.exceptions import CollectError, LLMError, ParseError
from app.core.vocabulary import Industry, Region
from app.graph.runner import event_to_graph_input, run_graph
from app.llm.gateway import LLMGateway
from app.models.collector_source import CollectorSource
from app.models.event import (
    EventStatus,
    compute_content_hash,
    compute_title_hash,
    compute_url_hash,
)
from app.repositories import collector_source_repository, event_repository
from app.repositories.filter_rule_repository import get_filter_rules

logger = structlog.get_logger()

# Caps parser.py's LLM extraction fallback per cycle (shared across the list
# page + every detail page in one run_collection_cycle call) -- see
# LLMFallbackBudget's docstring for why this isn't unbounded.
MAX_LLM_PARSE_FALLBACKS_PER_CYCLE = 5

# Tasks fired via asyncio.create_task() must be referenced somewhere until
# they complete, or the event loop may garbage-collect them mid-flight -- a
# well-known asyncio pitfall, not a cosmetic detail.
_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@dataclass
class CollectorRunSummary:
    source_id: str
    fetched: int = 0
    created: int = 0
    deduped: int = 0
    filtered_out: int = 0
    triggered_analysis: int = 0
    errors: list[str] = field(default_factory=list)


def _map_tag(value: str | None, vocabulary: type) -> str | None:
    if value is not None and value in vocabulary:
        return value
    if value is not None:
        logger.warning(
            "collector_tag_outside_vocabulary",
            value=value,
            vocabulary=vocabulary.__name__,
        )
    return None


async def _persist_collected_event(
    session: AsyncSession,
    *,
    source: CollectorSource,
    parsed,
    region: str | None,
    industry: str | None,
    filter_metadata: dict[str, Any],
    status: str,
    filter_score: float | None,
):
    return await event_repository.create_collected_event(
        session,
        collector_source_id=source.id,
        title=parsed.title,
        content=parsed.content,
        source_url=parsed.url,
        source_name=source.name,
        published_at=parsed.published_at,
        region=region,
        industry=industry,
        url_hash=compute_url_hash(parsed.url),
        title_hash=compute_title_hash(parsed.title),
        content_hash=compute_content_hash(parsed.content),
        filter_score=filter_score,
        status=status,
        metadata=filter_metadata,
    )


async def run_collection_cycle(
    source: CollectorSource,
    *,
    session: AsyncSession,
    crawler: Crawler,
    llm_gateway: LLMGateway,
    graph: CompiledStateGraph,
    session_factory: async_sessionmaker,
    background_tasks: BackgroundTasks | None,
) -> CollectorRunSummary:
    """fetch -> parse -> dedup -> filter(1) -> filter(2) -> create Event ->
    trigger analysis if it passed. Each item's crawl/parse errors are caught
    individually so one bad item doesn't abort the rest of the source."""
    summary = CollectorRunSummary(source_id=str(source.id))
    region = _map_tag(source.region_tags[0] if source.region_tags else None, Region)
    industry = _map_tag(
        source.industry_tags[0] if source.industry_tags else None, Industry
    )

    llm_fallback_budget = LLMFallbackBudget(MAX_LLM_PARSE_FALLBACKS_PER_CYCLE)

    try:
        list_doc = await crawler.fetch(source.list_url)
        links = await extract_list_links(
            list_doc.html,
            # Relative hrefs on the list page resolve against the list
            # page's own URL, not the site's base_url (domain root) --
            # confirmed as a real bug onboarding 重庆市住建委: a relative
            # "./202512/xxx.html" needs the list page's full directory
            # (.../zwxx_166/gsgg/), which base_url (just the domain) drops,
            # producing 10/10 404s. base_url is metadata, not a link-
            # resolution base.
            source.list_url,
            source.parser_type,
            gateway=llm_gateway,
            budget=llm_fallback_budget,
        )
    except (CollectError, ParseError) as exc:
        summary.errors.append(str(exc))
        logger.error(
            "collector_list_fetch_failed", source_id=summary.source_id, error=str(exc)
        )
        return summary

    # Caps how many items one cycle processes -- list pages are newest-first
    # (confirmed onboarding real sources), so this is "latest N", not an
    # arbitrary truncation. Without a cap a dense source (e.g. a public
    # resource trading platform with dozens of items per page) makes every
    # single scheduled run take as long as the slowest/most LLM-fallback-
    # heavy item on the page; anything past the cap is picked up next cycle
    # instead (COLLECTOR_MAX_ITEMS_PER_RUN in .env, default 5), not lost.
    max_items = get_settings().collector_max_items_per_run
    if len(links) > max_items:
        logger.debug(
            "collector_list_links_truncated",
            source_id=summary.source_id,
            found=len(links),
            kept=max_items,
        )
        links = links[:max_items]

    rules = await get_filter_rules(session)

    for url in links:
        summary.fetched += 1

        # Cheap url_hash-only pre-check (app/collector/dedup.py) -- skips the
        # fetch+parse entirely for items already collected on a prior cycle,
        # rather than re-fetching/re-parsing (and, now that parsing can fall
        # back to an LLM call, potentially re-billing) every item on the
        # list page every single run.
        if await url_already_collected(session, url):
            summary.deduped += 1
            logger.info(
                "collector_item_deduped_by_url", source_id=summary.source_id, url=url
            )
            continue

        try:
            raw = await crawler.fetch(url)
            parsed = await parse_detail(
                raw,
                source.parser_type,
                source.name,
                gateway=llm_gateway,
                budget=llm_fallback_budget,
            )
        except (CollectError, ParseError) as exc:
            summary.errors.append(str(exc))
            logger.error(
                "collector_item_failed",
                source_id=summary.source_id,
                url=url,
                error=str(exc),
            )
            continue

        duplicate = await find_duplicate(
            session, url=parsed.url, title=parsed.title, content=parsed.content
        )
        if duplicate is not None:
            summary.deduped += 1
            logger.info(
                "collector_item_deduped",
                source_id=summary.source_id,
                url=url,
                matched_event_id=str(duplicate.id),
            )
            continue

        decision = rule_filter(parsed, rules)
        filter_metadata: dict[str, Any] = {
            "attachments": parsed.attachments,
            "layer1": {
                "passed": decision.passed,
                "reason": decision.reason,
                "matched_include": decision.matched_include,
                "matched_exclude": decision.matched_exclude,
            },
        }

        if not decision.passed:
            await _persist_collected_event(
                session,
                source=source,
                parsed=parsed,
                region=region,
                industry=industry,
                filter_metadata=filter_metadata,
                status=EventStatus.FILTERED_OUT,
                filter_score=0.0,
            )
            summary.created += 1
            summary.filtered_out += 1
            continue

        try:
            relevance = await llm_relevance_filter(
                llm_gateway, parsed=parsed, threshold=rules.relevance_threshold
            )
            filter_metadata["layer2"] = relevance.model_dump(mode="json")
            passed_layer2 = (
                relevance.confidence >= rules.relevance_threshold and relevance.relevant
            )
            filter_score = relevance.confidence
        except LLMError as exc:
            # Fail closed: an LLM outage must not silently flood Expert with
            # unfiltered volume (Phase 3 plan design judgment #3).
            summary.errors.append(str(exc))
            filter_metadata["layer2"] = {"error": str(exc)}
            passed_layer2 = False
            filter_score = None

        status = (
            EventStatus.WAITING_ANALYSIS if passed_layer2 else EventStatus.FILTERED_OUT
        )
        event = await _persist_collected_event(
            session,
            source=source,
            parsed=parsed,
            region=region,
            industry=industry,
            filter_metadata=filter_metadata,
            status=status,
            filter_score=filter_score,
        )
        summary.created += 1

        if not passed_layer2:
            summary.filtered_out += 1
            continue

        run_id = str(uuid.uuid4())
        event_dict = event_to_graph_input(event)
        if background_tasks is not None:
            background_tasks.add_task(
                run_graph, graph, event_dict, run_id, session_factory
            )
        else:
            _fire_and_forget(run_graph(graph, event_dict, run_id, session_factory))
        summary.triggered_analysis += 1

    return summary


class CollectorScheduler:
    """Wraps AsyncIOScheduler. Reads enabled collector_source rows once at
    start() and registers one CronTrigger.from_crontab(source.schedule) job
    per source (a bad cron string on one source doesn't block the others).
    Does NOT dynamically pick up collector_source changes after startup --
    restart the app. Accepted Phase 3 limitation."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker,
        crawler_factory,
        llm_gateway: LLMGateway,
        graph: CompiledStateGraph,
    ) -> None:
        self._scheduler = AsyncIOScheduler()
        self._session_factory = session_factory
        self._crawler_factory = crawler_factory
        self._llm_gateway = llm_gateway
        self._graph = graph

    async def _run_source_job(self, source_id) -> None:
        async with self._session_factory() as session:
            source = await collector_source_repository.get_source(session, source_id)
            if source is None or not source.enabled:
                return
            crawler = self._crawler_factory()
            try:
                summary = await run_collection_cycle(
                    source,
                    session=session,
                    crawler=crawler,
                    llm_gateway=self._llm_gateway,
                    graph=self._graph,
                    session_factory=self._session_factory,
                    background_tasks=None,
                )
                logger.info("collector_cycle_completed", **vars(summary))
            finally:
                await crawler.aclose()

    async def start(self) -> None:
        async with self._session_factory() as session:
            sources = await collector_source_repository.list_enabled_sources(session)
        for source in sources:
            try:
                trigger = CronTrigger.from_crontab(source.schedule)
            except ValueError as exc:
                logger.error(
                    "collector_bad_schedule",
                    source_id=str(source.id),
                    schedule=source.schedule,
                    error=str(exc),
                )
                continue
            self._scheduler.add_job(
                self._run_source_job, trigger, args=[source.id], id=str(source.id)
            )
        self._scheduler.start()

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
