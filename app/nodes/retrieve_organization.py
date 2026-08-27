from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import RAGError
from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.knowledge.retriever import search_organization_candidates
from app.schemas.analysis import EventAnalysis


def make_retrieve_organization_node(
    session_factory: async_sessionmaker,
) -> Callable[[OpportunityState], Awaitable[dict]]:
    @log_node("retrieve_organization")
    async def retrieve_organization(state: OpportunityState) -> dict:
        event_analysis = EventAnalysis.model_validate(state["event_analysis"])
        try:
            async with session_factory() as session:
                items = await search_organization_candidates(session, event_analysis)
        except Exception as exc:
            raise RAGError(f"retrieve_organization failed: {exc}") from exc
        return {
            "organization_context": [item.model_dump(mode="json") for item in items]
        }

    return retrieve_organization
