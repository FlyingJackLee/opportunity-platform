import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import PushBranchPayload
from app.models.push_record import PushRecordStatus, RecipientType
from app.repositories import event_repository, push_record_repository


def make_archive_node(
    session_factory: async_sessionmaker,
) -> Callable[[PushBranchPayload], Awaitable[dict]]:
    """Send-dispatched per department branch -- same pattern as
    calculate_score, deliberately NOT a shared join (see the Phase 4 plan's
    "corrected design" section: a shared join here would run once per
    arrival wave, not once with all branches' data, since branches take a
    different number of hops to get here). Each invocation writes its own
    push_record and applies an order-independent conditional update to
    Event.status, then a plain add_edge("archive", END) ends this branch --
    no coordination with sibling branches needed."""

    @log_node("archive")
    async def archive(payload: PushBranchPayload) -> dict:
        push_result = payload["push_result"]

        if not payload["should_push"]:
            status = PushRecordStatus.SKIPPED
            channel = None
            recipient_type = RecipientType.NONE
            recipient_id = None
            message = None
            sent_at = None
            error = payload.get("skip_reason")
        else:
            status = push_result["status"]
            channel = "DINGTALK"
            recipient_type = payload["recipient_type"]
            recipient_id = payload["recipient_id"]
            message = payload["message"]
            sent_at = (
                datetime.fromisoformat(push_result["sent_at"])
                if push_result.get("sent_at")
                else datetime.now(UTC)
            )
            error = push_result.get("error")

        owner = payload.get("owner")
        owner_id = uuid.UUID(owner["id"]) if owner else None

        async with session_factory() as session:
            await push_record_repository.create_record(
                session,
                event_id=uuid.UUID(payload["event_id"]),
                expert_run_id=uuid.UUID(payload["run_id"]),
                department_id=payload["department_id"],
                organization_id=payload["organization_id"],
                channel=channel,
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                owner_id=owner_id,
                status=status,
                message=message,
                sent_at=sent_at,
                error=error,
            )
            if status == PushRecordStatus.SENT:
                await event_repository.mark_pushed(
                    session, uuid.UUID(payload["event_id"])
                )
            else:
                await event_repository.mark_archived_unless_pushed(
                    session, uuid.UUID(payload["event_id"])
                )

        return {}

    return archive
