import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.knowledge.ingestion import ingest_capability
from app.repositories import capability_repository
from app.schemas.capability import CapabilityCreate, CapabilityRead, CapabilityUpdate

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


@router.get("", response_model=list[CapabilityRead])
async def list_capabilities_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[CapabilityRead]:
    capabilities = await capability_repository.list_all(session)
    return [CapabilityRead.model_validate(c) for c in capabilities]


@router.get("/{capability_id}", response_model=CapabilityRead)
async def get_capability_endpoint(
    capability_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CapabilityRead:
    capability = await capability_repository.get(session, capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail="capability not found")
    return CapabilityRead.model_validate(capability)


@router.post("", response_model=CapabilityRead)
async def create_capability_endpoint(
    payload: CapabilityCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> CapabilityRead:
    capability = await ingest_capability(
        session,
        request.app.state.llm_gateway,
        id=uuid.uuid4(),
        **payload.model_dump(),
    )
    await session.commit()
    return CapabilityRead.model_validate(capability)


@router.patch("/{capability_id}", response_model=CapabilityRead)
async def update_capability_endpoint(
    capability_id: uuid.UUID,
    payload: CapabilityUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> CapabilityRead:
    """ingest_capability is a full upsert -- merge the patch onto the
    existing row first, same tradeoff as knowledge.py's update endpoint."""
    existing = await capability_repository.get(session, capability_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="capability not found")
    updates = payload.model_dump(exclude_unset=True)
    capability = await ingest_capability(
        session,
        request.app.state.llm_gateway,
        id=capability_id,
        name=updates.get("name", existing.name),
        scenarios=updates.get("scenarios", existing.scenarios),
        industries=updates.get("industries", existing.industries),
        solutions=updates.get("solutions", existing.solutions),
        cases=updates.get("cases", existing.cases),
        description=updates.get("description", existing.description),
        status=existing.status,
    )
    await session.commit()
    return CapabilityRead.model_validate(capability)


@router.post("/{capability_id}/deactivate", response_model=CapabilityRead)
async def deactivate_capability_endpoint(
    capability_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CapabilityRead:
    capability = await capability_repository.set_status(session, capability_id, "INACTIVE")
    if capability is None:
        raise HTTPException(status_code=404, detail="capability not found")
    return CapabilityRead.model_validate(capability)


@router.post("/{capability_id}/activate", response_model=CapabilityRead)
async def activate_capability_endpoint(
    capability_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CapabilityRead:
    capability = await capability_repository.set_status(session, capability_id, "ACTIVE")
    if capability is None:
        raise HTTPException(status_code=404, detail="capability not found")
    return CapabilityRead.model_validate(capability)
