from typing import Any

import structlog
from langgraph.graph.state import CompiledStateGraph

from app.core.logging import bind_run_context

logger = structlog.get_logger()


async def run_graph(
    graph: CompiledStateGraph, event: dict[str, Any], run_id: str
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
