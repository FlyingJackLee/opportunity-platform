from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import RAGError
from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.knowledge.retriever import search_industry_knowledge
from app.llm.gateway import LLMGateway
from app.schemas.analysis import EventAnalysis


def make_retrieve_industry_node(
    gateway: LLMGateway, session_factory: async_sessionmaker
) -> Callable[[OpportunityState], Awaitable[dict]]:
    @log_node("retrieve_industry")
    async def retrieve_industry(state: OpportunityState) -> dict:
        event_analysis = EventAnalysis.model_validate(state["event_analysis"])
        try:
            async with session_factory() as session:
                items = await search_industry_knowledge(
                    session, gateway, event_analysis
                )
        except Exception as exc:
            raise RAGError(f"retrieve_industry failed: {exc}") from exc
        return {"industry_context": [item.model_dump(mode="json") for item in items]}

    return retrieve_industry
