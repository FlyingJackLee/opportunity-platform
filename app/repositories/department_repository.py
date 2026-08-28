import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department

UNKNOWN = "UNKNOWN"


async def department_exists(session: AsyncSession, department_id: str) -> bool:
    """spec §72: department=UNKNOWN is a sanctioned fallback, not a fabrication."""
    if department_id == UNKNOWN:
        return True
    try:
        dept_uuid = uuid.UUID(department_id)
    except ValueError:
        return False
    stmt = select(Department.id).where(Department.id == dept_uuid)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def get_by_id(session: AsyncSession, department_id: str) -> Department | None:
    """Tolerant of the UNKNOWN sentinel (ADR-0002) -- returns None rather
    than raising, matching department_exists's guard style."""
    if department_id == UNKNOWN:
        return None
    try:
        dept_uuid = uuid.UUID(department_id)
    except ValueError:
        return None
    return await session.get(Department, dept_uuid)


async def get(session: AsyncSession, department_id: uuid.UUID) -> Department | None:
    """Admin-API counterpart to get_by_id -- real UUID, no UNKNOWN tolerance."""
    return await session.get(Department, department_id)


async def list_all(
    session: AsyncSession, organization_id: uuid.UUID | None = None
) -> list[Department]:
    stmt = select(Department).order_by(Department.name)
    if organization_id is not None:
        stmt = stmt.where(Department.organization_id == organization_id)
    return list((await session.execute(stmt)).scalars().all())


async def create(session: AsyncSession, **fields) -> Department:
    dept = Department(**fields)
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    return dept


async def update(session: AsyncSession, department_id: uuid.UUID, **fields) -> Department | None:
    dept = await session.get(Department, department_id)
    if dept is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(dept, key, value)
    await session.commit()
    await session.refresh(dept)
    return dept


async def set_status(
    session: AsyncSession, department_id: uuid.UUID, status: str
) -> Department | None:
    dept = await session.get(Department, department_id)
    if dept is None:
        return None
    dept.status = status
    await session.commit()
    await session.refresh(dept)
    return dept
