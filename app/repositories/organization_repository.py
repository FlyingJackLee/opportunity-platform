import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization

UNKNOWN = "UNKNOWN"


async def organization_exists(session: AsyncSession, organization_id: str) -> bool:
    """spec §72: department/organization=UNKNOWN is a sanctioned fallback, not
    a fabrication -- mini_review's existence check must not flag it."""
    if organization_id == UNKNOWN:
        return True
    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        return False
    stmt = select(Organization.id).where(Organization.id == org_uuid)
    return (await session.execute(stmt)).scalar_one_or_none() is not None
