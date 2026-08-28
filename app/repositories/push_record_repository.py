import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_record import PushRecord


async def create_record(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    expert_run_id: uuid.UUID,
    department_id: str,
    organization_id: str,
    channel: str | None,
    recipient_type: str,
    recipient_id: str | None,
    owner_id: uuid.UUID | None,
    status: str,
    message: str | None,
    sent_at: datetime | None,
    error: str | None,
) -> PushRecord:
    record = PushRecord(
        event_id=event_id,
        expert_run_id=expert_run_id,
        department_id=department_id,
        organization_id=organization_id,
        channel=channel,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        owner_id=owner_id,
        status=status,
        message=message,
        sent_at=sent_at,
        error=error,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def list_for_run(
    session: AsyncSession, expert_run_id: uuid.UUID
) -> list[PushRecord]:
    stmt = select(PushRecord).where(PushRecord.expert_run_id == expert_run_id)
    return list((await session.execute(stmt)).scalars().all())
