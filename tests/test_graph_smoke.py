import uuid

import pytest

from app.core.config import get_settings
from app.graph.checkpoint import checkpointer_context, setup_checkpointer
from app.graph.graph import build_graph
from app.llm.providers.stub import StubLLMGateway


@pytest.mark.usefixtures("_test_database")
async def test_graph_runs_initialize_then_echo_and_persists_each_checkpoint() -> None:
    settings = get_settings()
    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        graph = build_graph(StubLLMGateway(), checkpointer)

        run_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": run_id}}

        final_state = await graph.ainvoke(
            {
                "run_id": run_id,
                "event": {"id": "evt-1", "title": "测试事件", "content": "测试内容"},
                "departments": [],
            },
            config=config,
        )

        assert final_state["status"] == "COMPLETED"
        assert final_state["expert_result"]["echoed_title"] == "测试事件"

        history = [snapshot async for snapshot in graph.aget_state_history(config)]
        # One checkpoint for the initial input, plus one after each node ran.
        assert len(history) >= 3

        # `snapshot.next` names the node about to run *after* that checkpoint,
        # so each node's completion shows up as its own checkpoint boundary:
        # right after `initialize` runs, `next == ("echo",)`; right after
        # `echo` runs (the run is done), `next == ()`.
        next_values = {snapshot.next for snapshot in history}
        assert ("echo",) in next_values
        assert () in next_values
