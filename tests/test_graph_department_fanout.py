import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.graph.checkpoint import checkpointer_context, setup_checkpointer
from app.graph.graph import build_graph
from app.llm.providers.stub import StubLLMGateway
from app.repositories.event_repository import create_event
from app.repositories.expert_run_repository import get_run
from app.schemas.event import EventCreate


@pytest.fixture
def session_factory():
    engine = create_async_engine(get_settings().database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.usefixtures("_test_database")
async def test_multi_department_fanout_scores_independently(
    session_factory, db_session
) -> None:
    """The default StubLLMGateway fixture mirrors spec §105's demo: two
    departments (城建处 LEAD, 科技信息处 SUPPORT) with different confidence,
    related_needs, and related_capabilities -- ADR-0002 requires each to get
    its own independently-computed score, not a shared one."""
    event = await create_event(
        db_session,
        EventCreate(
            title="XX市发布城市生命线安全工程实施方案",
            content="政策已明确提出基础设施风险监测相关建设任务",
            region="重庆市",
        ),
    )

    settings = get_settings()
    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        graph = build_graph(StubLLMGateway(), checkpointer, session_factory)

        run_id = str(uuid.uuid4())
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
            config={"configurable": {"thread_id": run_id}},
        )

    departments = final_state["departments"]
    assert len(departments) == 2
    scores = {d["department_id"]: d["score"] for d in departments}
    assert len(set(scores.values())) == 2, "each department must score independently"

    run = await get_run(db_session, uuid.UUID(run_id))
    assert run is not None
    assert run.status == "COMPLETED"
    assert len(run.result_json["departments"]) == 2


@pytest.mark.usefixtures("_test_database")
async def test_sentinel_branch_when_no_departments_identified(
    session_factory, db_session
) -> None:
    """When Expert Judge identifies zero departments/organizations, the graph
    must still reach finalize_result/COMPLETED via a synthetic UNKNOWN branch
    -- not hang after mini_review (design judgment #3, spec §104 principle 6)."""
    from app.schemas.expert import ExpertResult
    from app.schemas.review import ReviewResult

    event = await create_event(
        db_session,
        EventCreate(title="无法判断的事件", content="内容不足", region="重庆市"),
    )

    empty_expert_result = ExpertResult(
        needs=[],
        organizations=[],
        departments=[],
        capabilities=[],
        reason="信息不足",
        risks=[],
    )
    gateway = StubLLMGateway(
        fixture_overrides={
            "EXPERT_JUDGE": empty_expert_result,
            "MINI_REVIEW": ReviewResult(approved=True, adjustments=[], risk_note=""),
        }
    )

    settings = get_settings()
    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        graph = build_graph(gateway, checkpointer, session_factory)

        run_id = str(uuid.uuid4())
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
            config={"configurable": {"thread_id": run_id}},
        )

    assert final_state["status"] == "COMPLETED"
    assert len(final_state["departments"]) == 1
    assert final_state["departments"][0]["department_id"] == "UNKNOWN"
