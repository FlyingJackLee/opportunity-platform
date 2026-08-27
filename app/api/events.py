import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.graph.runner import run_graph
from app.models.event import EventStatus
from app.repositories.event_repository import create_event, get_event, set_event_status
from app.schemas.event import EventCreate, EventCreateResponse, EventRead

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.post("/events", response_model=EventRead)
async def create_event_endpoint(
    payload: EventCreate,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """spec §20 -- create only. Triggering analysis is a separate call
    (/analyze, /reanalyze below) now that Phase 2 makes analysis a real,
    meaningful, separately-triggerable action rather than Phase 1's
    combined create+trigger shortcut."""
    event = await create_event(session, payload)
    return EventRead.model_validate(event)


def _trigger_run(
    event, request: Request, background_tasks: BackgroundTasks
) -> EventCreateResponse:
    run_id = str(uuid.uuid4())
    event_dict: dict[str, Any] = {
        "id": str(event.id),
        "title": event.title,
        "content": event.content,
    }
    background_tasks.add_task(
        run_graph,
        request.app.state.graph,
        event_dict,
        run_id,
        request.app.state.session_factory,
    )
    return EventCreateResponse(event_id=event.id, run_id=run_id, status="PROCESSING")


@router.post("/events/{event_id}/analyze", response_model=EventCreateResponse)
async def analyze_event_endpoint(
    event_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventCreateResponse:
    """spec §82/§83: async trigger, returns run_id immediately. 409 if a run
    is already in flight for this event (analyze, unlike reanalyze, guards
    against duplicate concurrent triggers)."""
    event = await get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    if event.status == EventStatus.ANALYZING:
        raise HTTPException(status_code=409, detail="event is already being analyzed")

    await set_event_status(session, event_id, EventStatus.WAITING_ANALYSIS)
    return _trigger_run(event, request, background_tasks)


@router.post("/events/{event_id}/reanalyze", response_model=EventCreateResponse)
async def reanalyze_event_endpoint(
    event_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EventCreateResponse:
    """spec §82: always starts a new expert_run against the same event
    (ADR-0001 anticipates multiple runs per event) -- skips analyze's
    ANALYZING guard on purpose."""
    event = await get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")

    await set_event_status(session, event_id, EventStatus.WAITING_ANALYSIS)
    return _trigger_run(event, request, background_tasks)
