"""Admin CRUD endpoints for the config entities the frontend manages:
organization/department/knowledge_chunk/capability/collector_source/
customer_owner. Uses unique-per-test names (uuid4 suffix) rather than
resetting these tables between tests -- conftest.py's db_session fixture
deliberately leaves reference data alone (shared, session-scoped seed)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.usefixtures("_test_database")
async def test_organization_crud() -> None:
    name = f"测试单位-{uuid.uuid4().hex[:8]}"
    with TestClient(app) as client:
        create_response = client.post("/api/v1/organizations", json={"name": name})
        assert create_response.status_code == 200
        org = create_response.json()
        assert org["name"] == name
        assert org["status"] == "ACTIVE"

        list_response = client.get("/api/v1/organizations")
        assert org["id"] in [o["id"] for o in list_response.json()]

        update_response = client.patch(
            f"/api/v1/organizations/{org['id']}", json={"description": "更新后"}
        )
        assert update_response.json()["description"] == "更新后"

        deactivate_response = client.post(
            f"/api/v1/organizations/{org['id']}/deactivate"
        )
        assert deactivate_response.json()["status"] == "INACTIVE"


@pytest.mark.usefixtures("_test_database")
async def test_department_crud_filters_by_organization() -> None:
    with TestClient(app) as client:
        org = client.post(
            "/api/v1/organizations", json={"name": f"测试单位-{uuid.uuid4().hex[:8]}"}
        ).json()

        create_response = client.post(
            "/api/v1/departments",
            json={"organization_id": org["id"], "name": "测试处室"},
        )
        assert create_response.status_code == 200
        dept = create_response.json()
        assert dept["organization_id"] == org["id"]

        filtered = client.get(
            "/api/v1/departments", params={"organization_id": org["id"]}
        ).json()
        assert [d["id"] for d in filtered] == [dept["id"]]

        deactivate_response = client.post(f"/api/v1/departments/{dept['id']}/deactivate")
        assert deactivate_response.json()["status"] == "INACTIVE"


@pytest.mark.usefixtures("_test_database")
async def test_knowledge_chunk_crud_computes_embedding_and_updates() -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/knowledge-chunks",
            json={
                "title": "测试知识条目",
                "content": "测试内容",
                "industry": "住建",
            },
        )
        assert create_response.status_code == 200
        chunk = create_response.json()
        assert chunk["title"] == "测试知识条目"
        assert "embedding" not in chunk

        update_response = client.patch(
            f"/api/v1/knowledge-chunks/{chunk['id']}", json={"topic": "新主题"}
        )
        assert update_response.json()["topic"] == "新主题"
        # unrelated fields survive a partial update
        assert update_response.json()["title"] == "测试知识条目"

        deactivate_response = client.post(
            f"/api/v1/knowledge-chunks/{chunk['id']}/deactivate"
        )
        assert deactivate_response.json()["status"] == "INACTIVE"


@pytest.mark.usefixtures("_test_database")
async def test_capability_crud_computes_embedding_and_updates() -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/capabilities",
            json={"name": f"测试能力-{uuid.uuid4().hex[:8]}", "scenarios": ["场景A"]},
        )
        assert create_response.status_code == 200
        capability = create_response.json()
        assert "embedding" not in capability

        update_response = client.patch(
            f"/api/v1/capabilities/{capability['id']}",
            json={"description": "新描述"},
        )
        assert update_response.json()["description"] == "新描述"
        assert update_response.json()["scenarios"] == ["场景A"]


@pytest.mark.usefixtures("_test_database")
async def test_collector_source_crud() -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/collectors",
            json={
                "name": f"测试信息源-{uuid.uuid4().hex[:8]}",
                "source_type": "GOV_WEB",
                "list_url": "https://example.invalid/list",
                "schedule": "0 */2 * * *",
                "parser_type": "GOV_GENERIC",
                "enabled": False,
            },
        )
        assert create_response.status_code == 200
        source = create_response.json()
        assert source["enabled"] is False

        update_response = client.patch(
            f"/api/v1/collectors/{source['id']}", json={"priority": 5}
        )
        assert update_response.json()["priority"] == 5

        enable_response = client.post(f"/api/v1/collectors/{source['id']}/enable")
        assert enable_response.json()["enabled"] is True

        disable_response = client.post(f"/api/v1/collectors/{source['id']}/disable")
        assert disable_response.json()["enabled"] is False


@pytest.mark.usefixtures("_test_database")
async def test_customer_owner_update_and_disable() -> None:
    with TestClient(app) as client:
        org = client.post(
            "/api/v1/organizations", json={"name": f"测试单位-{uuid.uuid4().hex[:8]}"}
        ).json()
        owner = client.post(
            "/api/v1/customer-owners",
            json={"organization_id": org["id"], "owner_name": "张三"},
        ).json()

        update_response = client.patch(
            f"/api/v1/customer-owners/{owner['id']}",
            json={"dingtalk_user_id": "zhangsan001"},
        )
        assert update_response.json()["dingtalk_user_id"] == "zhangsan001"

        disable_response = client.post(f"/api/v1/customer-owners/{owner['id']}/disable")
        assert disable_response.json()["enabled"] is False
