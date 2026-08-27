from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability import Capability


async def capability_exists(session: AsyncSession, name: str) -> bool:
    """Capabilities are referenced by name (ExpertResult.capabilities[].capability
    is a str, not an id) -- spec §43."""
    stmt = select(Capability.id).where(Capability.name == name)
    return (await session.execute(stmt)).scalar_one_or_none() is not None
