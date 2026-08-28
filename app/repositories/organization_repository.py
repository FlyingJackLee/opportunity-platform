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


async def get_by_id(session: AsyncSession, organization_id: str) -> Organization | None:
    """Tolerant of the UNKNOWN sentinel (ADR-0002) -- returns None rather
    than raising, matching organization_exists's guard style."""
    if organization_id == UNKNOWN:
        return None
    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        return None
    return await session.get(Organization, org_uuid)


async def get(session: AsyncSession, organization_id: uuid.UUID) -> Organization | None:
    """Admin-API counterpart to get_by_id -- takes a real UUID, no UNKNOWN
    tolerance (a 404 on a bad id is the right behavior for the admin UI)."""
    return await session.get(Organization, organization_id)


async def list_all(session: AsyncSession) -> list[Organization]:
    stmt = select(Organization).order_by(Organization.name)
    return list((await session.execute(stmt)).scalars().all())


async def create(session: AsyncSession, **fields) -> Organization:
    org = Organization(**fields)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


async def update(
    session: AsyncSession, organization_id: uuid.UUID, **fields
) -> Organization | None:
    org = await session.get(Organization, organization_id)
    if org is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(org, key, value)
    await session.commit()
    await session.refresh(org)
    return org


async def set_status(
    session: AsyncSession, organization_id: uuid.UUID, status: str
) -> Organization | None:
    org = await session.get(Organization, organization_id)
    if org is None:
        return None
    org.status = status
    await session.commit()
    await session.refresh(org)
    return org
