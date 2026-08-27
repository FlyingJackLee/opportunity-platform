import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.expert_run_repository import get_run
from app.schemas.run import RunStatusResponse

router = APIRouter(prefix="/api/v1", tags=["runs"])


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> RunStatusResponse:
    """Reads the expert_run table (closes the Phase 1 TODO that read
    straight off the LangGraph checkpointer as a stand-in)."""
    run = await get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunStatusResponse(
        run_id=str(run.id),
        status=run.status,
        values=run.result_json if run.status == "COMPLETED" else None,
        error=run.error,
    )
