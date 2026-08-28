import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.expert_run_repository import get_run
from app.repositories.push_record_repository import list_for_run
from app.schemas.run import PushSummary, RunStatusResponse

router = APIRouter(prefix="/api/v1", tags=["runs"])


@router.get("/graph/mermaid")
async def get_graph_mermaid(request: Request) -> dict[str, str]:
    """Static node topology (spec §69), not per-run execution state -- draws
    straight off the compiled graph LangGraph already builds
    (app.state.graph, see app/graph/graph.py), no LangGraph Platform/server
    involved (see the "LangGraph 官方 React 组件" discussion: that requires a
    real Platform deployment; this is the free part of the same library)."""
    graph = request.app.state.graph.get_graph()
    return {"mermaid": graph.draw_mermaid()}


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> RunStatusResponse:
    """Reads the expert_run table (closes the Phase 1 TODO that read
    straight off the LangGraph checkpointer as a stand-in). Push outcomes
    (spec §106 Trace) are read from push_record at request time rather than
    duplicated into expert_run.result_json -- keeps Expert's judgment output
    and Push's execution outcome in their own tables (ADR-0001's spirit)."""
    run = await get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    records = await list_for_run(session, run_id)
    push = [
        PushSummary(
            department_id=r.department_id,
            organization_id=r.organization_id,
            recipient_type=r.recipient_type,
            recipient_id=r.recipient_id,
            status=r.status,
            sent_at=r.sent_at,
            error=r.error,
        )
        for r in records
    ]

    return RunStatusResponse(
        run_id=str(run.id),
        status=run.status,
        values=run.result_json if run.status == "COMPLETED" else None,
        error=run.error,
        push=push or None,
    )
