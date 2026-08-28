import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories import organization_repository
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationRead])
async def list_organizations_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[OrganizationRead]:
    orgs = await organization_repository.list_all(session)
    return [OrganizationRead.model_validate(o) for o in orgs]


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization_endpoint(
    organization_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    org = await organization_repository.get(session, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return OrganizationRead.model_validate(org)


@router.post("", response_model=OrganizationRead)
async def create_organization_endpoint(
    payload: OrganizationCreate,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    org = await organization_repository.create(session, **payload.model_dump())
    return OrganizationRead.model_validate(org)


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization_endpoint(
    organization_id: uuid.UUID,
    payload: OrganizationUpdate,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    org = await organization_repository.update(
        session, organization_id, **payload.model_dump()
    )
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return OrganizationRead.model_validate(org)


@router.post("/{organization_id}/deactivate", response_model=OrganizationRead)
async def deactivate_organization_endpoint(
    organization_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    org = await organization_repository.set_status(session, organization_id, "INACTIVE")
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return OrganizationRead.model_validate(org)


@router.post("/{organization_id}/activate", response_model=OrganizationRead)
async def activate_organization_endpoint(
    organization_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    org = await organization_repository.set_status(session, organization_id, "ACTIVE")
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return OrganizationRead.model_validate(org)


@router.delete("/{organization_id}", status_code=204)
async def delete_organization_endpoint(
    organization_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Hard delete, for clearing out test/seed rows -- day-to-day lifecycle
    management should use /deactivate instead (see organization_repository.
    delete's docstring)."""
    try:
        deleted = await organization_repository.delete(session, organization_id)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="该单位下还有部门或客户经理记录，请先删除它们",
        ) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="organization not found")
