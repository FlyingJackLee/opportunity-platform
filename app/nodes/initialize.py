import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.graph.version import GRAPH_VERSION
from app.models.event import EventStatus
from app.repositories import event_repository, expert_run_repository


def make_initialize_node(
    session_factory: async_sessionmaker,
) -> Callable[[OpportunityState], Awaitable[dict]]:
    """Creates the expert_run row (status=RUNNING) and marks the Event
    ANALYZING -- both closing a Phase 1 gap where Event.status was set at
    creation and never touched again."""

    @log_node("initialize")
    async def initialize(state: OpportunityState) -> dict:
        run_id = uuid.UUID(state["run_id"])
        event_id = uuid.UUID(state["event"]["id"])
        async with session_factory() as session:
            await expert_run_repository.create_run(
                session, run_id=run_id, event_id=event_id, graph_version=GRAPH_VERSION
            )
            await event_repository.set_event_status(
                session, event_id, EventStatus.ANALYZING
            )
        return {"status": "RUNNING", "departments": []}

    return initialize
