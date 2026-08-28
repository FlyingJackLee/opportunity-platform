from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.delivery.channel import DeliveryChannel
from app.graph.retry import is_transient_error
from app.graph.routing import route_to_push_fanout, route_to_score_fanout
from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway
from app.nodes.analyze_event import make_analyze_event_node
from app.nodes.archive import make_archive_node
from app.nodes.build_message import make_build_message_node
from app.nodes.calculate_score import make_calculate_score_node
from app.nodes.expert_judge import make_expert_judge_node
from app.nodes.finalize_result import make_finalize_result_node
from app.nodes.initialize import make_initialize_node
from app.nodes.mini_review import make_mini_review_node
from app.nodes.resolve_owner import make_resolve_owner_node
from app.nodes.retrieve_capability import make_retrieve_capability_node
from app.nodes.retrieve_industry import make_retrieve_industry_node
from app.nodes.retrieve_organization import make_retrieve_organization_node
from app.nodes.send_dingtalk import make_send_dingtalk_node
from app.nodes.should_push import make_should_push_node


def build_graph(
    gateway: LLMGateway,
    checkpointer,
    session_factory: async_sessionmaker,
    delivery_channel: DeliveryChannel,
    settings: Settings,
) -> CompiledStateGraph:
    """Phase 4 (Delivery/Push) extends Phase 2's chain:

        ... -> finalize_result
                    | route_to_push_fanout (Send, N >= 1)
                    v
              should_push -> [NO] -> Send(archive)
                           -> [YES] -> Send(resolve_owner) -> Send(build_message)
                                       -> Send(send_dingtalk) -> Send(archive)
              archive -> END

    should_push/resolve_owner/build_message/send_dingtalk return
    Command(goto=Send(next_node, payload)) rather than plain dicts -- Send
    branches share no ambient state, so the running PushBranchPayload is
    threaded explicitly through every hop (see app/graph/state.py's
    PushBranchPayload docstring). archive is itself Send-dispatched, like
    calculate_score -- NOT a shared join: each department branch writes its
    own push_record and applies an order-independent conditional update to
    Event.status, then reaches END independently. A shared join was
    considered and empirically ruled out (it would run once per arrival wave
    rather than once with all branches present, since branches take a
    different number of hops to arrive) -- see the Phase 4 plan.
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

    graph.add_node("should_push", make_should_push_node())
    graph.add_node("resolve_owner", make_resolve_owner_node(session_factory))
    graph.add_node("build_message", make_build_message_node(session_factory))
    graph.add_node(
        "send_dingtalk",
        make_send_dingtalk_node(delivery_channel, settings),
        retry_policy=retry,
    )
    graph.add_node("archive", make_archive_node(session_factory))

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
    graph.add_conditional_edges("finalize_result", route_to_push_fanout)
    graph.add_edge("archive", END)

    return graph.compile(checkpointer=checkpointer)
