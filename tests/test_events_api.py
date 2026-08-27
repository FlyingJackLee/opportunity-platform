import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.event_repository import get_event


@pytest.mark.usefixtures("_test_database")
async def test_manual_event_analyze_produces_structured_judgment(db_session) -> None:
    """Phase 2's acceptance test: Event -> 结构化商务研判结果."""
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
        event_id = create_response.json()["id"]

        analyze_response = client.post(f"/api/v1/events/{event_id}/analyze")
        assert analyze_response.status_code == 200
        run_body = analyze_response.json()
        assert run_body["status"] == "PROCESSING"

        run_response = client.get(f"/api/v1/runs/{run_body['run_id']}")
        assert run_response.status_code == 200
        run_status = run_response.json()
        assert run_status["status"] == "COMPLETED", run_status
        assert run_status["error"] is None

        result = run_status["values"]
        assert result["needs"]
        assert result["organizations"]
        assert result["departments"]
        assert result["capabilities"]
        assert result["recommended_action"]

    event = await get_event(db_session, uuid.UUID(event_id))
    assert event is not None
    assert event.status == "ANALYZED"


@pytest.mark.usefixtures("_test_database")
def test_manual_event_create_rejects_region_outside_controlled_vocabulary() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/events",
            json={"title": "t", "content": "c", "region": "火星"},
        )
    assert response.status_code == 422


@pytest.mark.usefixtures("_test_database")
def test_analyze_unknown_event_returns_404() -> None:
    with TestClient(app) as client:
        response = client.post(f"/api/v1/events/{uuid.uuid4()}/analyze")
    assert response.status_code == 404


@pytest.mark.usefixtures("_test_database")
async def test_analyze_while_already_analyzing_returns_409(db_session) -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/events", json={"title": "t", "content": "c", "region": "重庆市"}
        )
        event_id = create_response.json()["id"]

        from app.models.event import EventStatus
        from app.repositories.event_repository import set_event_status

        await set_event_status(db_session, uuid.UUID(event_id), EventStatus.ANALYZING)

        response = client.post(f"/api/v1/events/{event_id}/analyze")
    assert response.status_code == 409


@pytest.mark.usefixtures("_test_database")
async def test_reanalyze_creates_a_new_run(db_session) -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/events",
            json={
                "title": "XX市发布城市生命线安全工程实施方案",
                "content": "政策已明确提出基础设施风险监测相关建设任务",
                "region": "重庆市",
            },
        )
        event_id = create_response.json()["id"]

        first = client.post(f"/api/v1/events/{event_id}/analyze")
        second = client.post(f"/api/v1/events/{event_id}/reanalyze")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] != second.json()["run_id"]
