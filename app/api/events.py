import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.graph.runner import event_to_graph_input, run_graph
from app.models.event import EventStatus, compute_content_hash
from app.repositories import event_repository
from app.repositories.event_repository import (
    create_event,
    get_by_content_hash,
    get_event,
    list_events,
    set_event_status,
)
from app.repositories.expert_run_repository import list_runs_for_event
from app.schemas.event import EventCreate, EventCreateResponse, EventDetail, EventRead
from app.schemas.run import RunSummary

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.post("/events", response_model=EventRead)
async def create_event_endpoint(
    payload: EventCreate,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """spec §20 -- create only. Triggering analysis is a separate call
    (/analyze, /reanalyze below) now that Phase 2 makes analysis a real,
    meaningful, separately-triggerable action rather than Phase 1's
    combined create+trigger shortcut.

    event.content_hash has a real unique constraint (spec §13 dedup) -- this
    endpoint has no pre-check the way Collector's create_collected_event does
    (find_duplicate before insert), so a duplicate submission hit a raw
    IntegrityError/500 in practice. Catch it and point at the existing event
    instead."""
    try:
        event = await create_event(session, payload)
    except IntegrityError as exc:
        await session.rollback()
        existing = await get_by_content_hash(session, compute_content_hash(payload.content))
        detail = "content already exists as an event (spec §13 dedup)"
        if existing is not None:
            detail = f"{detail}: {existing.id}"
        raise HTTPException(status_code=409, detail=detail) from exc
    return EventRead.model_validate(event)


@router.get("/events", response_model=list[EventRead])
async def list_events_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    """Admin monitoring page (spec §106 Trace) -- newest first, capped at
    200 (list_events's default); no pagination yet at one-期 scale."""
    events = await list_events(session)
    return [EventRead.model_validate(e) for e in events]


@router.delete("/events/{event_id}", status_code=204)
async def delete_event_endpoint(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await event_repository.delete(session, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="event not found")


@router.get("/events/{event_id}", response_model=EventDetail)
async def get_event_endpoint(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> EventDetail:
    event = await get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    runs = await list_runs_for_event(session, event_id)
    return EventDetail(
        **EventRead.model_validate(event).model_dump(),
        runs=[RunSummary.model_validate(r) for r in runs],
    )


def _trigger_run(
    event, request: Request, background_tasks: BackgroundTasks
) -> EventCreateResponse:
    run_id = str(uuid.uuid4())
    event_dict = event_to_graph_input(event)
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
