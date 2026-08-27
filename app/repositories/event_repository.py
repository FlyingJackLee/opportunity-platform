import uuid

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


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> Event | None:
    return await session.get(Event, event_id)


async def set_event_status(
    session: AsyncSession, event_id: uuid.UUID, status: str
) -> None:
    event = await session.get(Event, event_id)
    if event is not None:
        event.status = status
        await session.commit()
