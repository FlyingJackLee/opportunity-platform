import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories import department_repository
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate

router = APIRouter(prefix="/api/v1/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
async def list_departments_endpoint(
    organization_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[DepartmentRead]:
    depts = await department_repository.list_all(session, organization_id)
    return [DepartmentRead.model_validate(d) for d in depts]


@router.get("/{department_id}", response_model=DepartmentRead)
async def get_department_endpoint(
    department_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DepartmentRead:
    dept = await department_repository.get(session, department_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="department not found")
    return DepartmentRead.model_validate(dept)


@router.post("", response_model=DepartmentRead)
async def create_department_endpoint(
    payload: DepartmentCreate,
    session: AsyncSession = Depends(get_session),
) -> DepartmentRead:
    dept = await department_repository.create(session, **payload.model_dump())
    return DepartmentRead.model_validate(dept)


@router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department_endpoint(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    session: AsyncSession = Depends(get_session),
) -> DepartmentRead:
    dept = await department_repository.update(session, department_id, **payload.model_dump())
    if dept is None:
        raise HTTPException(status_code=404, detail="department not found")
    return DepartmentRead.model_validate(dept)


@router.post("/{department_id}/deactivate", response_model=DepartmentRead)
async def deactivate_department_endpoint(
    department_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DepartmentRead:
    dept = await department_repository.set_status(session, department_id, "INACTIVE")
    if dept is None:
        raise HTTPException(status_code=404, detail="department not found")
    return DepartmentRead.model_validate(dept)


@router.post("/{department_id}/activate", response_model=DepartmentRead)
async def activate_department_endpoint(
    department_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DepartmentRead:
    dept = await department_repository.set_status(session, department_id, "ACTIVE")
    if dept is None:
        raise HTTPException(status_code=404, detail="department not found")
    return DepartmentRead.model_validate(dept)


@router.delete("/{department_id}", status_code=204)
async def delete_department_endpoint(
    department_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    try:
        deleted = await department_repository.delete(session, department_id)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="该部门下还有客户经理记录，请先删除它们"
        ) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="department not found")
