from fastapi import APIRouter, HTTPException, Request

from app.schemas.run import RunStatusResponse

router = APIRouter(prefix="/api/v1", tags=["runs"])


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str, request: Request) -> RunStatusResponse:
    """Reads straight off the LangGraph checkpointer — Phase 1 has no
    `expert_run` table (spec §55/§80 belong to Phase 2/4). Once that table
    exists, switch this to reading it instead (cheaper, indexable, supports
    listing) rather than the checkpointer, which is meant for graph execution
    state, not a query surface."""
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": run_id}}
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="run not found")
    values = snapshot.values
    return RunStatusResponse(
        run_id=run_id,
        status=values.get("status", "UNKNOWN"),
        values=values,
        error=values.get("error"),
    )
