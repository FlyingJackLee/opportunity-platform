from collections.abc import Awaitable, Callable

from langgraph.types import Command, Send

from app.core.logging import log_node
from app.graph.state import PushBranchPayload

PUSH_LEVELS = {"A", "B"}


def level_should_push(level: str) -> bool:
    """spec §58's literal default: A/B -> Push, C/WATCH -> Archive. No DB
    config table (Phase 4 plan design judgment #2) -- there's no operator
    knob to expose yet since Digest (C's other option) isn't built."""
    return level in PUSH_LEVELS


def make_should_push_node() -> Callable[[PushBranchPayload], Awaitable[Command]]:
    """Pure Code, no DB, no RetryPolicy (not in spec §71's retry-eligible list)."""

    @log_node("should_push")
    async def should_push(payload: PushBranchPayload) -> Command:
        if level_should_push(payload["level"]):
            return Command(goto=Send("resolve_owner", {**payload, "should_push": True}))
        return Command(
            goto=Send(
                "archive",
                {
                    **payload,
                    "should_push": False,
                    "skip_reason": "level_below_push_threshold",
                },
            )
        )

    return should_push
