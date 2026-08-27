import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.graph.checkpoint import checkpointer_context, setup_checkpointer
from app.graph.graph import build_graph
from app.llm.providers.stub import StubLLMGateway
from app.repositories.event_repository import create_event
from app.schemas.event import EventCreate


@pytest.fixture
def session_factory():
    engine = create_async_engine(get_settings().database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.usefixtures("_test_database")
async def test_graph_runs_full_chain_and_persists_each_node_as_a_checkpoint(
    session_factory, db_session
) -> None:
    event = await create_event(
        db_session, EventCreate(title="测试事件", content="测试内容", region="重庆市")
    )

    settings = get_settings()
    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        graph = build_graph(StubLLMGateway(), checkpointer, session_factory)

        run_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": run_id}}

        final_state = await graph.ainvoke(
            {
                "run_id": run_id,
                "event": {
                    "id": str(event.id),
                    "title": event.title,
                    "content": event.content,
                },
                "departments": [],
            },
            config=config,
        )

        assert final_state["status"] == "COMPLETED"
        assert final_state["final_result"] is not None

        history = [snapshot async for snapshot in graph.aget_state_history(config)]
        next_values = {snapshot.next for snapshot in history}
        # finalize_result's checkpoint is the run's end (next == ()).
        assert () in next_values
