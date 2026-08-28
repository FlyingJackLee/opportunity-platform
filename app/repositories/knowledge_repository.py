import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk


async def list_all(session: AsyncSession) -> list[KnowledgeChunk]:
    stmt = select(KnowledgeChunk).order_by(KnowledgeChunk.title)
    return list((await session.execute(stmt)).scalars().all())


async def get(session: AsyncSession, chunk_id: uuid.UUID) -> KnowledgeChunk | None:
    return await session.get(KnowledgeChunk, chunk_id)


async def set_status(
    session: AsyncSession, chunk_id: uuid.UUID, status: str
) -> KnowledgeChunk | None:
    chunk = await session.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        return None
    chunk.status = status
    await session.commit()
    await session.refresh(chunk)
    return chunk


async def delete(session: AsyncSession, chunk_id: uuid.UUID) -> bool:
    chunk = await session.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        return False
    await session.delete(chunk)
    await session.commit()
    return True
