import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.crawler import StaticCrawler
from app.collector.scheduler import run_collection_cycle
from app.core.db import get_session
from app.repositories import collector_source_repository
from app.repositories.collector_source_repository import get_source, list_sources
from app.schemas.collector import (
    CollectorRunResponse,
    CollectorSourceCreate,
    CollectorSourceRead,
    CollectorSourceUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["collectors"])


@router.get("/collectors", response_model=list[CollectorSourceRead])
async def list_collectors_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[CollectorSourceRead]:
    sources = await list_sources(session)
    return [CollectorSourceRead.model_validate(s) for s in sources]


@router.post("/collectors", response_model=CollectorSourceRead)
async def create_collector_endpoint(
    payload: CollectorSourceCreate,
    session: AsyncSession = Depends(get_session),
) -> CollectorSourceRead:
    source = await collector_source_repository.create(session, **payload.model_dump())
    return CollectorSourceRead.model_validate(source)


@router.patch("/collectors/{source_id}", response_model=CollectorSourceRead)
async def update_collector_endpoint(
    source_id: uuid.UUID,
    payload: CollectorSourceUpdate,
    session: AsyncSession = Depends(get_session),
) -> CollectorSourceRead:
    source = await collector_source_repository.update(
        session, source_id, **payload.model_dump()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="collector source not found")
    return CollectorSourceRead.model_validate(source)


@router.post("/collectors/{source_id}/enable", response_model=CollectorSourceRead)
async def enable_collector_endpoint(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CollectorSourceRead:
    source = await collector_source_repository.set_enabled(session, source_id, True)
    if source is None:
        raise HTTPException(status_code=404, detail="collector source not found")
    return CollectorSourceRead.model_validate(source)


@router.post("/collectors/{source_id}/disable", response_model=CollectorSourceRead)
async def disable_collector_endpoint(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CollectorSourceRead:
    source = await collector_source_repository.set_enabled(session, source_id, False)
    if source is None:
        raise HTTPException(status_code=404, detail="collector source not found")
    return CollectorSourceRead.model_validate(source)


@router.post("/collectors/{source_id}/run", response_model=CollectorRunResponse)
async def run_collector_endpoint(
    source_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> CollectorRunResponse:
    """spec §21. Manual trigger for one collection cycle -- passes the real
    FastAPI BackgroundTasks so TestClient runs it synchronously, same
    no-polling property app/api/events.py's /analyze already has."""
    source = await get_source(session, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="collector source not found")

    crawler = StaticCrawler()
    try:
        summary = await run_collection_cycle(
            source,
            session=session,
            crawler=crawler,
            llm_gateway=request.app.state.llm_gateway,
            graph=request.app.state.graph,
            session_factory=request.app.state.session_factory,
            background_tasks=background_tasks,
        )
    finally:
        await crawler.aclose()

    return CollectorRunResponse(
        source_id=summary.source_id,
        fetched=summary.fetched,
        created=summary.created,
        deduped=summary.deduped,
        filtered_out=summary.filtered_out,
        triggered_analysis=summary.triggered_analysis,
        errors=summary.errors,
    )


@router.delete("/collectors/{source_id}", status_code=204)
async def delete_collector_endpoint(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    try:
        deleted = await collector_source_repository.delete(session, source_id)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="该信息源下还有已采集的 Event 记录，无法删除（可以直接停用）",
        ) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="collector source not found")
