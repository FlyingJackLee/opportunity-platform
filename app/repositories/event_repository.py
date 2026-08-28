import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus, compute_content_hash
from app.schemas.event import EventCreate


async def create_event(session: AsyncSession, payload: EventCreate) -> Event:
    event = Event(
        title=payload.title,
        content=payload.content,
        source_type=payload.source_type,
        source_name=payload.source_name,
        source_url=payload.source_url,
        region=payload.region,
        industry=payload.industry,
        status=EventStatus.NEW,
        content_hash=compute_content_hash(payload.content),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def create_collected_event(
    session: AsyncSession,
    *,
    collector_source_id: uuid.UUID,
    title: str,
    content: str,
    source_url: str,
    source_name: str | None,
    published_at: datetime | None,
    region: str | None,
    industry: str | None,
    url_hash: str,
    title_hash: str,
    content_hash: str,
    filter_score: float | None,
    status: str,
    metadata: dict | None,
) -> Event:
    """Second creation path distinct from create_event (which serves the
    EventCreate/manual-API shape) -- Collector's inputs (extra hashes,
    caller-supplied status/filter_score, collector_source_id) don't fit that
    schema. spec §17: source_type is always "PUBLIC_WEB" for Collector-created
    events (a different vocabulary from CollectorSource.source_type -- see
    CONTEXT.md)."""
    event = Event(
        title=title,
        content=content,
        source_type="PUBLIC_WEB",
        source_name=source_name,
        source_url=source_url,
        published_at=published_at,
        collected_at=datetime.now(UTC),
        region=region,
        industry=industry,
        status=status,
        content_hash=content_hash,
        url_hash=url_hash,
        title_hash=title_hash,
        filter_score=filter_score,
        metadata_=metadata,
        collector_source_id=collector_source_id,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> Event | None:
    return await session.get(Event, event_id)


async def list_events(session: AsyncSession, limit: int = 200) -> list[Event]:
    stmt = select(Event).order_by(Event.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def set_event_status(
    session: AsyncSession, event_id: uuid.UUID, status: str
) -> None:
    event = await session.get(Event, event_id)
    if event is not None:
        event.status = status
        await session.commit()


async def mark_pushed(session: AsyncSession, event_id: uuid.UUID) -> None:
    """Unconditional: PUSHED, once written by any department branch, must
    never be overwritten back to ARCHIVED by a sibling branch that didn't
    push (archive.py is a per-branch node, not a synchronized join -- see
    the Phase 4 plan's corrected graph design)."""
    await session.execute(
        text("UPDATE event SET status = :status WHERE id = :id"),
        {"status": EventStatus.PUSHED, "id": event_id},
    )
    await session.commit()


async def mark_archived_unless_pushed(
    session: AsyncSession, event_id: uuid.UUID
) -> None:
    """Only downgrades to ARCHIVED if no sibling branch already got this
    Event to PUSHED -- order-independent, no coordination between the
    per-branch archive invocations required."""
    await session.execute(
        text("UPDATE event SET status = :status WHERE id = :id AND status != :pushed"),
        {"status": EventStatus.ARCHIVED, "id": event_id, "pushed": EventStatus.PUSHED},
    )
    await session.commit()
