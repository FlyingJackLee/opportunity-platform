from collections.abc import Awaitable, Callable

import structlog
from pydantic import BaseModel

from app.core.logging import log_llm_usage, log_node
from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway


class EchoResult(BaseModel):
    echoed_title: str


def make_echo_node(
    gateway: LLMGateway,
) -> Callable[[OpportunityState], Awaitable[dict]]:
    """DELETE in Phase 2 — replaced by analyze_event. Exists only to prove the
    LLMGateway plumbing works end-to-end inside a real graph run: FastAPI →
    LangGraph → LLMGateway → Postgres checkpointer. Not one of spec §68's
    official nodes; a factory closure (not module-level) so it can capture the
    single LLMGateway instance built once at app startup."""

    @log_node("echo")
    async def echo(state: OpportunityState) -> dict:
        title = state["event"]["title"]
        result = await gateway.structured_generate(
            task_type="ECHO",
            prompt=f"Echo back: {title}",
            schema=EchoResult,
        )
        log_llm_usage(
            structlog.get_logger(),
            model=result.model,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
        )
        return {
            "expert_result": {
                "echoed_title": title,
                "gateway_response": result.data.model_dump(),
            },
            "status": "COMPLETED",
        }

    return echo
