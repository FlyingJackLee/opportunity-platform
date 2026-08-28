import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability import Capability


async def capability_exists(session: AsyncSession, name: str) -> bool:
    """Capabilities are referenced by name (ExpertResult.capabilities[].capability
    is a str, not an id) -- spec §43."""
    stmt = select(Capability.id).where(Capability.name == name)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def list_all(session: AsyncSession) -> list[Capability]:
    stmt = select(Capability).order_by(Capability.name)
    return list((await session.execute(stmt)).scalars().all())


async def get(session: AsyncSession, capability_id: uuid.UUID) -> Capability | None:
    return await session.get(Capability, capability_id)


async def set_status(
    session: AsyncSession, capability_id: uuid.UUID, status: str
) -> Capability | None:
    capability = await session.get(Capability, capability_id)
    if capability is None:
        return None
    capability.status = status
    await session.commit()
    await session.refresh(capability)
    return capability


async def delete(session: AsyncSession, capability_id: uuid.UUID) -> bool:
    capability = await session.get(Capability, capability_id)
    if capability is None:
        return False
    await session.delete(capability)
    await session.commit()
    return True
