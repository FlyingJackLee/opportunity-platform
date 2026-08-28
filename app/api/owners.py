from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.customer_owner_repository import create_owner, list_owners
from app.schemas.owner import CustomerOwnerCreate, CustomerOwnerRead

router = APIRouter(prefix="/api/v1", tags=["owners"])


@router.get("/customer-owners", response_model=list[CustomerOwnerRead])
async def list_customer_owners_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[CustomerOwnerRead]:
    owners = await list_owners(session)
    return [CustomerOwnerRead.model_validate(o) for o in owners]


@router.post("/customer-owners", response_model=CustomerOwnerRead)
async def create_customer_owner_endpoint(
    payload: CustomerOwnerCreate,
    session: AsyncSession = Depends(get_session),
) -> CustomerOwnerRead:
    owner = await create_owner(
        session,
        organization_id=payload.organization_id,
        department_id=payload.department_id,
        owner_name=payload.owner_name,
        owner_user_id=payload.owner_user_id,
        dingtalk_user_id=payload.dingtalk_user_id,
        enabled=payload.enabled,
    )
    return CustomerOwnerRead.model_validate(owner)
