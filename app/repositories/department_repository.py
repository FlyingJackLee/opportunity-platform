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
