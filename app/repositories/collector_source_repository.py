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
