import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.graph.runner import run_graph
from app.repositories.event_repository import create_event
from app.schemas.event import EventCreate, EventCreateResponse

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.post("/events", response_model=EventCreateResponse)
async def create_event_endpoint(
    payload: EventCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventCreateResponse:
    """Persists the Event, then immediately triggers a graph run in the
    background (spec §83/§84 — the task queue decides *when* the graph runs;
    BackgroundTasks is enough at Phase 1's concurrency level).

    Deliberately combines spec §20 (create) and §82 (analyze) into one call for
    Phase 1's acceptance test ("手工输入 Event → Graph 正常执行"). If manual
    events actually need a human-review gap between creation and analysis,
    split this into two endpoints — flagged in the Phase 1 plan for
    confirmation."""
    event = await create_event(session, payload)
    run_id = str(uuid.uuid4())
    event_dict: dict[str, Any] = {
        "id": str(event.id),
        "title": event.title,
        "content": event.content,
    }
    background_tasks.add_task(run_graph, request.app.state.graph, event_dict, run_id)
    return EventCreateResponse(event_id=event.id, run_id=run_id, status="PROCESSING")
