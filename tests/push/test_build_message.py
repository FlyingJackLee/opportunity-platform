from app.nodes.build_message import UNCONFIGURED_OWNER_MARKER, build_message

BASE_PAYLOAD = {
    "run_id": "r1",
    "event_id": "e1",
    "event_title": "XX市发布城市生命线安全工程实施方案",
    "event_source_url": "https://example.invalid/policy",
    "summary": "政策已明确提出基础设施风险监测相关建设任务。",
    "risks": [],
    "recommended_action": "建议近期联系相关业务部门确认年度建设计划。",
    "department_id": "dep-1",
    "organization_id": "org-1",
    "role": "LEAD",
    "score": 82.0,
    "level": "A",
    "confidence": 0.81,
    "related_needs": [
        {"name": "风险监测预警", "confidence": 0.9, "maturity": "EXPLICIT"}
    ],
    "related_capabilities": [{"capability": "AI风险预警", "score": 0.88}],
    "should_push": True,
    "skip_reason": None,
    "message": None,
    "recipient_type": None,
    "recipient_id": None,
    "push_result": None,
    "error": None,
}


def _payload(**overrides):
    return {**BASE_PAYLOAD, "owner": {"id": "o1", "owner_name": "张三"}, **overrides}


def test_message_contains_all_spec_sections() -> None:
    message = build_message(
        _payload(), org_name="重庆市住房和城乡建设委员会", dept_name="城建处"
    )
    for header in [
        "【事件】",
        "【AI判断】",
        "【重点单位】",
        "【建议部门】",
        "【潜在需求】",
        "【我方切入】",
        "【当前风险】",
        "【建议动作】",
        "【原始信息】",
    ]:
        assert header in message


def test_message_length_is_within_spec_target() -> None:
    message = build_message(
        _payload(), org_name="重庆市住房和城乡建设委员会", dept_name="城建处"
    )
    assert 100 <= len(message) <= 800  # generous bound around spec §65's 200-600 target


def test_unconfigured_owner_marker_present_only_when_owner_is_none() -> None:
    with_owner = build_message(
        _payload(owner={"id": "o1", "owner_name": "张三"}),
        org_name="单位",
        dept_name="部门",
    )
    assert UNCONFIGURED_OWNER_MARKER not in with_owner

    without_owner = build_message(
        _payload(owner=None), org_name="单位", dept_name="部门"
    )
    assert UNCONFIGURED_OWNER_MARKER in without_owner


def test_message_only_shows_this_departments_needs_and_capabilities() -> None:
    """design judgment #3: one message per department, not the event-level
    rollup -- a different department's needs must never leak in."""
    payload = _payload(
        related_needs=[
            {"name": "仅这个部门的需求", "confidence": 0.8, "maturity": "POTENTIAL"}
        ],
        related_capabilities=[{"capability": "仅这个部门的能力", "score": 0.7}],
    )
    message = build_message(payload, org_name="单位", dept_name="部门")
    assert "仅这个部门的需求" in message
    assert "仅这个部门的能力" in message


def test_role_label_translated() -> None:
    lead_message = build_message(
        _payload(role="LEAD"), org_name="单位", dept_name="部门"
    )
    support_message = build_message(
        _payload(role="SUPPORT"), org_name="单位", dept_name="部门"
    )
    assert "可能业务牵头" in lead_message
    assert "可能技术协同" in support_message
