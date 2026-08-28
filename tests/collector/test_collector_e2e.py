import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.collector_source import CollectorSource
from app.models.event import Event


async def _seed_source(db_session, base_url: str) -> str:
    source = CollectorSource(
        id=uuid.uuid4(),
        name=f"测试信源-{uuid.uuid4().hex[:8]}",
        source_type="GOV_WEB",
        base_url=base_url,
        list_url=f"{base_url}/list.html",
        enabled=True,
        schedule="0 */2 * * *",
        parser_type="GOV_GENERIC",
        industry_tags=["住建"],
        region_tags=["重庆市"],
        priority=0,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return str(source.id)


@pytest.mark.usefixtures("_test_database")
async def test_collector_run_creates_events_analyzes_and_dedupes(
    db_session, local_fixture_server
) -> None:
    source_id = await _seed_source(db_session, local_fixture_server)

    with TestClient(app) as client:
        first = client.post(f"/api/v1/collectors/{source_id}/run")
        assert first.status_code == 200
        summary = first.json()

        # list.html links to 3 detail pages; the republished one dedupes
        # against detail_1 within this same cycle (title/content match).
        assert summary["fetched"] == 3
        assert summary["created"] == 2
        assert summary["deduped"] == 1
        assert (
            summary["filtered_out"] == 1
        )  # detail_2 (reading-club notice) has no include keywords
        assert (
            summary["triggered_analysis"] == 1
        )  # only detail_1 passes both filter layers

        events_result = await db_session.execute(select(Event))
        events = list(events_result.scalars().all())
        assert len(events) == 2

        # Phase 4 extends the pipeline automatically through Push -- the
        # triggered analysis uses the default StubLLMGateway fixture (2
        # B-level departments, both with a configured Customer Owner), so
        # this now finishes PUSHED, not ANALYZED.
        pushed = [e for e in events if e.status == "PUSHED"]
        filtered_out = [e for e in events if e.status == "FILTERED_OUT"]
        assert len(pushed) == 1
        assert len(filtered_out) == 1

        passed_event = pushed[0]
        assert passed_event.url_hash is not None
        assert passed_event.title_hash is not None
        assert passed_event.content_hash is not None
        assert (
            passed_event.filter_score is not None and passed_event.filter_score >= 0.6
        )
        assert passed_event.collector_source_id == uuid.UUID(source_id)

        # Second run of the same fixtures: everything should dedupe now.
        second = client.post(f"/api/v1/collectors/{source_id}/run")
        assert second.status_code == 200
        second_summary = second.json()
        assert second_summary["created"] == 0
        assert second_summary["deduped"] == 3

        list_response = client.get("/api/v1/collectors")
        assert list_response.status_code == 200
        assert any(s["id"] == source_id for s in list_response.json())


@pytest.mark.usefixtures("_test_database")
def test_run_unknown_collector_returns_404() -> None:
    with TestClient(app) as client:
        response = client.post(f"/api/v1/collectors/{uuid.uuid4()}/run")
    assert response.status_code == 404
