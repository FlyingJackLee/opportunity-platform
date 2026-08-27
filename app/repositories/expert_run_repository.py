import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expert_run import ExpertRun


async def create_run(
    session: AsyncSession, *, run_id: uuid.UUID, event_id: uuid.UUID, graph_version: str
) -> ExpertRun:
    run = ExpertRun(
        id=run_id,
        event_id=event_id,
        graph_version=graph_version,
        status="RUNNING",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def complete_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    *,
    score: float,
    level: str,
    confidence: float,
    result_json: dict,
    model_version: str | None,
    event_prompt_version: str | None,
    judge_prompt_version: str | None,
    review_prompt_version: str | None,
) -> None:
    run = await session.get(ExpertRun, run_id)
    if run is None:
        return
    run.status = "COMPLETED"
    run.completed_at = datetime.now(UTC)
    run.score = score
    run.level = level
    run.confidence = confidence
    run.result_json = result_json
    run.model_version = model_version
    run.event_prompt_version = event_prompt_version
    run.judge_prompt_version = judge_prompt_version
    run.review_prompt_version = review_prompt_version
    await session.commit()


async def fail_run(session: AsyncSession, run_id: uuid.UUID, error: str) -> None:
    run = await session.get(ExpertRun, run_id)
    if run is None:
        return
    run.status = "FAILED"
    run.completed_at = datetime.now(UTC)
    run.error = error
    await session.commit()


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> ExpertRun | None:
    return await session.get(ExpertRun, run_id)


async def get_latest_run_for_event(
    session: AsyncSession, event_id: uuid.UUID
) -> ExpertRun | None:
    stmt = (
        select(ExpertRun)
        .where(ExpertRun.event_id == event_id)
        .order_by(ExpertRun.started_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()
