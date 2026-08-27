from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.graph.retry import is_transient_error
from app.graph.routing import route_to_score_fanout
from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway
from app.nodes.analyze_event import make_analyze_event_node
from app.nodes.calculate_score import make_calculate_score_node
from app.nodes.expert_judge import make_expert_judge_node
from app.nodes.finalize_result import make_finalize_result_node
from app.nodes.initialize import make_initialize_node
from app.nodes.mini_review import make_mini_review_node
from app.nodes.retrieve_capability import make_retrieve_capability_node
from app.nodes.retrieve_industry import make_retrieve_industry_node
from app.nodes.retrieve_organization import make_retrieve_organization_node


def build_graph(
    gateway: LLMGateway, checkpointer, session_factory: async_sessionmaker
) -> CompiledStateGraph:
    """Phase 2 (Expert MVP):

        initialize -> analyze_event
                    -> retrieve_industry     \\
                    -> retrieve_organization  }-> expert_judge -> mini_review
                    -> retrieve_capability    /
                                                    | route_to_score_fanout (Send, N >= 1)
                                                    v
                                              calculate_score -> finalize_result -> END

    retrieve_industry/organization/capability run in parallel off
    analyze_event (spec §70 permits either; parallel is idiomatic here) and
    join into expert_judge once all three complete. mini_review is one global
    pass; calculate_score fans out per department (ADR-0002).
    """
    retry = RetryPolicy(max_attempts=3, retry_on=is_transient_error)

    graph = StateGraph(OpportunityState)
    graph.add_node("initialize", make_initialize_node(session_factory))
    graph.add_node(
        "analyze_event",
        make_analyze_event_node(gateway, session_factory),
        retry_policy=retry,
    )
    graph.add_node(
        "retrieve_industry",
        make_retrieve_industry_node(gateway, session_factory),
        retry_policy=retry,
    )
    graph.add_node(
        "retrieve_organization",
        make_retrieve_organization_node(session_factory),
        retry_policy=retry,
    )
    graph.add_node(
        "retrieve_capability",
        make_retrieve_capability_node(gateway, session_factory),
        retry_policy=retry,
    )
    graph.add_node(
        "expert_judge",
        make_expert_judge_node(gateway, session_factory),
        retry_policy=retry,
    )
    graph.add_node(
        "mini_review",
        make_mini_review_node(gateway, session_factory),
        retry_policy=retry,
    )
    graph.add_node("calculate_score", make_calculate_score_node(session_factory))
    graph.add_node("finalize_result", make_finalize_result_node(session_factory))

    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "analyze_event")
    graph.add_edge("analyze_event", "retrieve_industry")
    graph.add_edge("analyze_event", "retrieve_organization")
    graph.add_edge("analyze_event", "retrieve_capability")
    graph.add_edge("retrieve_industry", "expert_judge")
    graph.add_edge("retrieve_organization", "expert_judge")
    graph.add_edge("retrieve_capability", "expert_judge")
    graph.add_edge("expert_judge", "mini_review")
    graph.add_conditional_edges("mini_review", route_to_score_fanout)
    graph.add_edge("calculate_score", "finalize_result")
    graph.add_edge("finalize_result", END)

    return graph.compile(checkpointer=checkpointer)
