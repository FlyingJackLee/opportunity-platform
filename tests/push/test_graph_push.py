import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.ids import seed_uuid
from app.core.seed_keys import ORG_FAGAI_WEI
from app.delivery.dingtalk import DingTalkAdapter
from app.delivery.recording import RecordingDeliveryChannel
from app.graph.checkpoint import checkpointer_context, setup_checkpointer
from app.graph.graph import build_graph
from app.llm.providers.stub import StubLLMGateway
from app.models.push_record import PushRecord, PushRecordStatus, RecipientType
from app.repositories.event_repository import create_event
from app.repositories.expert_run_repository import get_run
from app.schemas.event import EventCreate
from app.schemas.expert import (
    CapabilityResult,
    DepartmentResult,
    ExpertResult,
    Need,
    NeedMaturity,
    OrganizationResult,
)
from app.schemas.review import ReviewResult

# Same natural key seed_phase2.py uses for this department -- no seed_keys
# constant exists for it since the seed script itself only inlines it, and
# this test intentionally reuses an org (ORG_FAGAI_WEI) that has NO
# customer_owner configured, to exercise the public-group fallback path.
DEPT_GAOJISHU_CHU = "dept:重庆市发展和改革委员会:高技术处"


@pytest.fixture
def session_factory():
    engine = create_async_engine(get_settings().database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.usefixtures("_test_database")
async def test_two_departments_push_independently_to_distinct_owners(
    session_factory, db_session
) -> None:
    """The default StubLLMGateway fixture (spec §105 demo): 城建处 has no
    department-level owner (falls back to Organization Owner 张三),
    科技信息处 has its own Department Owner 李四 -- CONTEXT.md's "no push
    dedup" rule means both get an independent SENT push_record even though
    both departments belong to the same organization."""
    event = await create_event(
        db_session,
        EventCreate(
            title="XX市发布城市生命线安全工程实施方案",
            content="政策已明确提出基础设施风险监测相关建设任务",
            region="重庆市",
        ),
    )

    channel = RecordingDeliveryChannel()
    settings = get_settings()
    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        graph = build_graph(
            StubLLMGateway(), checkpointer, session_factory, channel, settings
        )

        run_id = str(uuid.uuid4())
        await graph.ainvoke(
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

    records = (
        (
            await db_session.execute(
                select(PushRecord).where(PushRecord.expert_run_id == uuid.UUID(run_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 2
    assert {r.status for r in records} == {PushRecordStatus.SENT}
    recipient_ids = {r.recipient_id for r in records}
    assert recipient_ids == {"zhangsan_dingtalk", "lisi_dingtalk"}
    recipient_types = {r.recipient_id: r.recipient_type for r in records}
    assert recipient_types["zhangsan_dingtalk"] == RecipientType.ORGANIZATION_OWNER
    assert recipient_types["lisi_dingtalk"] == RecipientType.DEPARTMENT_OWNER

    assert len(channel.calls) == 2

    # db_session's identity map still holds the "NEW" instance it created
    # above; the graph updated the row through session_factory's own
    # connections, so refresh this specific object rather than trust the cache.
    await db_session.refresh(event)
    assert event.status == "PUSHED"

    run = await get_run(db_session, uuid.UUID(run_id))
    assert run.status == "COMPLETED"


@pytest.mark.usefixtures("_test_database")
async def test_no_owner_configured_falls_back_to_public_group(
    session_factory, db_session, local_dingtalk_server
) -> None:
    base_url, log = local_dingtalk_server
    event = await create_event(
        db_session,
        EventCreate(
            title="发改委相关数字经济事件",
            content="涉及数字经济专项资金申报",
            region="重庆市",
        ),
    )

    org_id = str(seed_uuid(ORG_FAGAI_WEI))
    dept_id = str(seed_uuid(DEPT_GAOJISHU_CHU))
    # High-confidence single department, no owner configured for ORG_FAGAI_WEI
    # anywhere -- guarantees an A/B score so should_push actually attempts
    # a send, hitting the public-group fallback (spec §62).
    expert_result = ExpertResult(
        needs=[
            Need(name="数字经济专项", confidence=0.9, maturity=NeedMaturity.EXPLICIT)
        ],
        organizations=[OrganizationResult(organization_id=org_id, score=0.9)],
        departments=[
            DepartmentResult(
                department_id=dept_id,
                organization_id=org_id,
                role="LEAD",
                confidence=0.9,
                related_needs=[
                    Need(
                        name="数字经济专项",
                        confidence=0.9,
                        maturity=NeedMaturity.EXPLICIT,
                    )
                ],
                related_capabilities=[
                    CapabilityResult(capability="数字经济咨询", score=0.9)
                ],
            )
        ],
        capabilities=[CapabilityResult(capability="数字经济咨询", score=0.9)],
        reason="数字经济专项资金申报，存在明确商务机会。",
        risks=[],
        recommended_action="建议联系高技术处确认申报进度。",
    )
    gateway = StubLLMGateway(
        fixture_overrides={
            "EXPERT_JUDGE": expert_result,
            "MINI_REVIEW": ReviewResult(approved=True, adjustments=[], risk_note=""),
        }
    )

    channel = DingTalkAdapter()
    settings = Settings(
        dingtalk_webhook_url=f"{base_url}/robot/main",
        dingtalk_webhook_secret="main-secret",
        dingtalk_public_group_webhook_url=f"{base_url}/robot/public",
        dingtalk_public_group_webhook_secret=None,
    )

    try:
        async with checkpointer_context(settings) as checkpointer:
            await setup_checkpointer(checkpointer)
            graph = build_graph(
                gateway, checkpointer, session_factory, channel, settings
            )

            run_id = str(uuid.uuid4())
            await graph.ainvoke(
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
    finally:
        await channel.aclose()

    records = (
        (
            await db_session.execute(
                select(PushRecord).where(PushRecord.expert_run_id == uuid.UUID(run_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    record = records[0]
    assert record.recipient_type == RecipientType.PUBLIC_GROUP
    assert record.status == PushRecordStatus.SENT
    assert "【暂未配置客户负责人】" in record.message

    public_requests = [r for r in log.requests if r["path"] == "/robot/public"]
    assert len(public_requests) == 1
    main_requests = [r for r in log.requests if r["path"] == "/robot/main"]
    assert len(main_requests) == 0


@pytest.mark.usefixtures("_test_database")
async def test_low_level_branch_is_archived_without_sending(
    session_factory, db_session
) -> None:
    """Mirrors test_graph_department_fanout.py's sentinel technique: an empty
    ExpertResult produces a WATCH-level branch that should_push routes
    straight to archive -- no owner resolution, no DingTalk call at all."""
    event = await create_event(
        db_session,
        EventCreate(title="无法判断的事件", content="内容不足", region="重庆市"),
    )

    gateway = StubLLMGateway(
        fixture_overrides={
            "EXPERT_JUDGE": ExpertResult(
                needs=[],
                organizations=[],
                departments=[],
                capabilities=[],
                reason="信息不足",
                risks=[],
            ),
            "MINI_REVIEW": ReviewResult(approved=True, adjustments=[], risk_note=""),
        }
    )
    channel = RecordingDeliveryChannel()
    settings = get_settings()

    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        graph = build_graph(gateway, checkpointer, session_factory, channel, settings)

        run_id = str(uuid.uuid4())
        await graph.ainvoke(
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

    assert channel.calls == []

    records = (
        (
            await db_session.execute(
                select(PushRecord).where(PushRecord.expert_run_id == uuid.UUID(run_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    assert records[0].status == PushRecordStatus.SKIPPED
    assert records[0].channel is None

    await db_session.refresh(event)
    assert event.status == "ARCHIVED"
