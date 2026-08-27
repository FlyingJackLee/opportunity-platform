import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.event_repository import get_event


@pytest.mark.usefixtures("_test_database")
async def test_manual_event_create_triggers_graph_run_end_to_end(db_session) -> None:
    """Phase 1's acceptance test: 手工输入 Event -> Graph 正常执行.

    TestClient is synchronous and drives BackgroundTasks to completion before
    a call returns, so no polling/sleep is needed here."""
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/events",
            json={
                "title": "XX市发布城市生命线安全工程实施方案",
                "content": "政策已明确提出基础设施风险监测相关建设任务",
                "region": "重庆市",
                "industry": "住建",
            },
        )
        assert create_response.status_code == 200
        body = create_response.json()
        assert body["status"] == "PROCESSING"

        run_response = client.get(f"/api/v1/runs/{body['run_id']}")
        assert run_response.status_code == 200
        run_body = run_response.json()
        assert run_body["status"] == "COMPLETED"
        assert run_body["error"] is None
        assert (
            run_body["values"]["expert_result"]["echoed_title"]
            == "XX市发布城市生命线安全工程实施方案"
        )

    event = await get_event(db_session, uuid.UUID(body["event_id"]))
    assert event is not None
    assert event.title == "XX市发布城市生命线安全工程实施方案"
    assert event.region == "重庆市"
    assert event.industry == "住建"


@pytest.mark.usefixtures("_test_database")
def test_manual_event_create_rejects_region_outside_controlled_vocabulary() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/events",
            json={"title": "t", "content": "c", "region": "火星"},
        )
    assert response.status_code == 422
