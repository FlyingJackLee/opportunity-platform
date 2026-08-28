import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories import customer_owner_repository
from app.repositories.customer_owner_repository import create_owner, list_owners
from app.schemas.owner import (
    CustomerOwnerCreate,
    CustomerOwnerRead,
    CustomerOwnerUpdate,
)

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


@router.patch("/customer-owners/{owner_id}", response_model=CustomerOwnerRead)
async def update_customer_owner_endpoint(
    owner_id: uuid.UUID,
    payload: CustomerOwnerUpdate,
    session: AsyncSession = Depends(get_session),
) -> CustomerOwnerRead:
    owner = await customer_owner_repository.update(session, owner_id, **payload.model_dump())
    if owner is None:
        raise HTTPException(status_code=404, detail="customer owner not found")
    return CustomerOwnerRead.model_validate(owner)


@router.post("/customer-owners/{owner_id}/enable", response_model=CustomerOwnerRead)
async def enable_customer_owner_endpoint(
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CustomerOwnerRead:
    owner = await customer_owner_repository.set_enabled(session, owner_id, True)
    if owner is None:
        raise HTTPException(status_code=404, detail="customer owner not found")
    return CustomerOwnerRead.model_validate(owner)


@router.post("/customer-owners/{owner_id}/disable", response_model=CustomerOwnerRead)
async def disable_customer_owner_endpoint(
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CustomerOwnerRead:
    owner = await customer_owner_repository.set_enabled(session, owner_id, False)
    if owner is None:
        raise HTTPException(status_code=404, detail="customer owner not found")
    return CustomerOwnerRead.model_validate(owner)
