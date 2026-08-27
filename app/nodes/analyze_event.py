from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway
from app.repositories.prompt_repository import get_active_prompt
from app.schemas.analysis import EventAnalysis


def make_analyze_event_node(
    gateway: LLMGateway, session_factory: async_sessionmaker
) -> Callable[[OpportunityState], Awaitable[dict]]:
    """spec §25: understands the event, does not make business judgments."""

    @log_node("analyze_event")
    async def analyze_event(state: OpportunityState) -> dict:
        event = state["event"]
        async with session_factory() as session:
            prompt = await get_active_prompt(session, "EVENT_ANALYZE")

        full_prompt = f"{prompt.content}\n\n【事件标题】\n{event['title']}\n\n【事件内容】\n{event['content']}"
        result = await gateway.structured_generate(
            task_type="EVENT_ANALYZE", prompt=full_prompt, schema=EventAnalysis
        )
        return {
            "event_analysis": result.data.model_dump(mode="json"),
            "event_prompt_version": prompt.version,
        }

    return analyze_event
