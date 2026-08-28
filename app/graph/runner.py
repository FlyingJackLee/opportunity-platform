import uuid
from typing import Any

import structlog
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import bind_run_context
from app.models.event import Event, EventStatus
from app.repositories import event_repository, expert_run_repository

logger = structlog.get_logger()


def event_to_graph_input(event: Event) -> dict[str, Any]:
    """Shared by app/api/events.py's manual trigger and
    app/collector/scheduler.py's auto-trigger, so both build graph input
    identically. source_url is included for Phase 4's build_message node
    (spec §65's "原始信息/查看原文" link)."""
    return {
        "id": str(event.id),
        "title": event.title,
        "content": event.content,
        "source_url": event.source_url,
    }


async def run_graph(
    graph: CompiledStateGraph,
    event: dict[str, Any],
    run_id: str,
    session_factory: async_sessionmaker,
) -> None:
    """Invokes the graph for one run. Catches anything a node lets escape so
    GET /runs/{run_id} always has a queryable terminal state, even on an
    uncaught node exception — nodes themselves only need to raise, not manage
    state.status on the failure path."""
    config = {"configurable": {"thread_id": run_id}}
    bind_run_context(run_id, event.get("id"))
    try:
        await graph.ainvoke(
            {"run_id": run_id, "event": event, "departments": []},
            config=config,
        )
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: this is the
        # last-resort backstop that guarantees a terminal run status no matter
        # what a node raises; narrowing it would defeat the purpose.
        logger.error("graph_run_failed", error=str(exc))
        await graph.aupdate_state(config, {"status": "FAILED", "error": str(exc)})
        async with session_factory() as session:
            await expert_run_repository.fail_run(session, uuid.UUID(run_id), str(exc))
            await event_repository.set_event_status(
                session, uuid.UUID(event["id"]), EventStatus.FAILED
            )
