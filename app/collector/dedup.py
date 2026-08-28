"""spec §13: three-tier dedup (URL / title normalization / content hash),
Phase 1 priority explicitly "URL + title normalization + content hash" (the
optional semantic/embedding tier is out of scope). A match on ANY of the
three hashes counts as a duplicate -- that's what catches "同一政策被多个网站
转载" (§13's stated motivation): a reprint has a different URL but identical
title/content."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import (
    Event,
    compute_content_hash,
    compute_title_hash,
    compute_url_hash,
)

DEFAULT_WINDOW_DAYS = 90


async def find_duplicate(
    session: AsyncSession,
    *,
    url: str,
    title: str,
    content: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> Event | None:
    """Bounded by collected_at >= now - window_days. B-tree equality lookups
    on the hash columns are already O(log n) regardless of table size -- the
    window is a documented scope limit (only recent reposts are caught), not
    a performance necessity."""
    url_hash = compute_url_hash(url)
    title_hash = compute_title_hash(title)
    content_hash = compute_content_hash(content)
    since = datetime.now(UTC) - timedelta(days=window_days)

    stmt = select(Event).where(
        Event.collected_at >= since,
        or_(
            Event.url_hash == url_hash,
            Event.title_hash == title_hash,
            Event.content_hash == content_hash,
        ),
    )
    return (await session.execute(stmt)).scalars().first()


async def url_already_collected(
    session: AsyncSession, url: str, window_days: int = DEFAULT_WINDOW_DAYS
) -> bool:
    """Cheap pre-check, url_hash only -- run before fetching/parsing the
    detail page at all, not just before storing. A source's list page shows
    the same recent items on every scheduled run; without this, every one of
    those already-collected items gets re-fetched and re-parsed on every
    cycle for no reason (and, once parser.py's LLM fallback exists, that
    means a real LLM call per already-seen item per cycle -- see the parsing
    cost discussion). This is a strict subset of find_duplicate's url_hash
    branch, so it never changes final dedup outcomes -- it only short-
    circuits the expensive fetch+parse for the common case. The rarer
    cross-source reprint case (different URL, same content) still needs
    find_duplicate after parsing, since content_hash isn't known yet here."""
    url_hash = compute_url_hash(url)
    since = datetime.now(UTC) - timedelta(days=window_days)
    stmt = select(Event.id).where(
        Event.collected_at >= since, Event.url_hash == url_hash
    )
    return (await session.execute(stmt)).scalars().first() is not None
