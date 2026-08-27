from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway
from app.nodes.echo import make_echo_node
from app.nodes.initialize import initialize


def build_graph(gateway: LLMGateway, checkpointer) -> CompiledStateGraph:
    """Phase 1: a two-node linear scaffold (initialize -> echo -> END) proving
    the LangGraph + Postgres checkpointer + LLMGateway wiring works end to end.
    No RetryPolicy attached yet — spec §71's retry-eligible nodes
    (analyze_event/retrieve_context/expert_judge/mini_review/send_dingtalk)
    don't exist until Phase 2/4; attaching retry semantics to the throwaway
    `echo` node would prove nothing durable."""
    graph = StateGraph(OpportunityState)
    graph.add_node("initialize", initialize)
    graph.add_node("echo", make_echo_node(gateway))
    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "echo")
    graph.add_edge("echo", END)
    return graph.compile(checkpointer=checkpointer)
