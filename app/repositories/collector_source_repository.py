import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collector_source import CollectorSource


async def get_source(
    session: AsyncSession, source_id: uuid.UUID
) -> CollectorSource | None:
    return await session.get(CollectorSource, source_id)


async def list_sources(session: AsyncSession) -> list[CollectorSource]:
    return list((await session.execute(select(CollectorSource))).scalars().all())


async def list_enabled_sources(session: AsyncSession) -> list[CollectorSource]:
    stmt = select(CollectorSource).where(CollectorSource.enabled.is_(True))
    return list((await session.execute(stmt)).scalars().all())


async def create(session: AsyncSession, **fields) -> CollectorSource:
    source = CollectorSource(**fields)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


async def update(session: AsyncSession, source_id: uuid.UUID, **fields) -> CollectorSource | None:
    source = await session.get(CollectorSource, source_id)
    if source is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(source, key, value)
    await session.commit()
    await session.refresh(source)
    return source


async def set_enabled(
    session: AsyncSession, source_id: uuid.UUID, enabled: bool
) -> CollectorSource | None:
    source = await session.get(CollectorSource, source_id)
    if source is None:
        return None
    source.enabled = enabled
    await session.commit()
    await session.refresh(source)
    return source
