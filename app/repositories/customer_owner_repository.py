import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_owner import CustomerOwner
from app.models.push_record import RecipientType

UNKNOWN = "UNKNOWN"


@dataclass
class OwnerMatch:
    owner: CustomerOwner
    recipient_type: str  # RecipientType.DEPARTMENT_OWNER | ORGANIZATION_OWNER


async def resolve_owner(
    session: AsyncSession, *, organization_id: str, department_id: str
) -> OwnerMatch | None:
    """Department Owner -> Organization Owner -> None (caller falls back to
    the public group, spec §60-62). Returns None gracefully -- "can't find
    owner" is not an error (spec §72), never raises for UNKNOWN/UNKNOWN or an
    unparseable id."""
    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        return None

    if department_id != UNKNOWN:
        try:
            dept_uuid = uuid.UUID(department_id)
        except ValueError:
            dept_uuid = None
        if dept_uuid is not None:
            stmt = select(CustomerOwner).where(
                CustomerOwner.organization_id == org_uuid,
                CustomerOwner.department_id == dept_uuid,
                CustomerOwner.enabled.is_(True),
            )
            owner = (await session.execute(stmt)).scalars().first()
            if owner is not None:
                return OwnerMatch(
                    owner=owner, recipient_type=RecipientType.DEPARTMENT_OWNER
                )

    stmt = select(CustomerOwner).where(
        CustomerOwner.organization_id == org_uuid,
        CustomerOwner.department_id.is_(None),
        CustomerOwner.enabled.is_(True),
    )
    owner = (await session.execute(stmt)).scalars().first()
    if owner is not None:
        return OwnerMatch(owner=owner, recipient_type=RecipientType.ORGANIZATION_OWNER)

    return None


async def list_owners(session: AsyncSession) -> list[CustomerOwner]:
    return list((await session.execute(select(CustomerOwner))).scalars().all())


async def create_owner(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    department_id: uuid.UUID | None,
    owner_name: str,
    owner_user_id: str | None,
    dingtalk_user_id: str | None,
    enabled: bool = True,
) -> CustomerOwner:
    owner = CustomerOwner(
        organization_id=organization_id,
        department_id=department_id,
        owner_name=owner_name,
        owner_user_id=owner_user_id,
        dingtalk_user_id=dingtalk_user_id,
        enabled=enabled,
    )
    session.add(owner)
    await session.commit()
    await session.refresh(owner)
    return owner
