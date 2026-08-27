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
