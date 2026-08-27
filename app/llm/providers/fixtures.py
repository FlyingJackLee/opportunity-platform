"""Task-type-aware canned responses for StubLLMGateway. Without these, the
generic type-based stub fills ExpertResult's list fields with [], which means
the Send()-based department fan-out (ADR-0002) never actually runs in any
test using the plain stub. Mirrors the spec §105 demo scenario exactly:
XX市《城市生命线安全工程实施方案》 -> 住建委 -> 城建处(LEAD)/科技信息处(SUPPORT).

Built once at import time (constructed through the real Pydantic schemas) so
a schema change that breaks these fixtures fails fast, not silently."""

from pydantic import BaseModel

from app.core.ids import seed_uuid
from app.core.seed_keys import (
    DEPT_CHENGJIAN_CHU,
    DEPT_KEJI_XINXI_CHU,
    ORG_ZHUJIAN_WEI,
)
from app.schemas.analysis import EventAnalysis, EventType, SignalLevel, Signals
from app.schemas.expert import (
    CapabilityResult,
    DepartmentResult,
    ExpertResult,
    Need,
    NeedMaturity,
    OrganizationResult,
)
from app.schemas.review import ReviewResult

_ORG_ID = str(seed_uuid(ORG_ZHUJIAN_WEI))
_DEPT_CHENGJIAN_ID = str(seed_uuid(DEPT_CHENGJIAN_CHU))
_DEPT_KEJI_ID = str(seed_uuid(DEPT_KEJI_XINXI_CHU))

_EVENT_ANALYZE_FIXTURE = EventAnalysis(
    event_type=EventType.POLICY,
    region="重庆市",
    industry=["住建"],
    topics=["城市生命线"],
    tasks=["建设基础设施风险监测能力"],
    objects=["燃气", "桥梁", "供水"],
    signals=Signals(
        project_signal=SignalLevel.MEDIUM,
        budget_signal=SignalLevel.UNKNOWN,
        procurement_signal=SignalLevel.UNKNOWN,
    ),
)

_EXPERT_JUDGE_FIXTURE = ExpertResult(
    needs=[
        Need(name="风险监测预警", confidence=0.90, maturity=NeedMaturity.EXPLICIT),
        Need(name="物联感知接入", confidence=0.75, maturity=NeedMaturity.POTENTIAL),
        Need(name="基础设施数据治理", confidence=0.70, maturity=NeedMaturity.POTENTIAL),
    ],
    organizations=[OrganizationResult(organization_id=_ORG_ID, score=0.91)],
    departments=[
        DepartmentResult(
            department_id=_DEPT_CHENGJIAN_ID,
            organization_id=_ORG_ID,
            role="LEAD",
            confidence=0.84,
            related_needs=[
                Need(
                    name="风险监测预警", confidence=0.90, maturity=NeedMaturity.EXPLICIT
                ),
                Need(
                    name="物联感知接入",
                    confidence=0.75,
                    maturity=NeedMaturity.POTENTIAL,
                ),
            ],
            related_capabilities=[
                CapabilityResult(capability="AI风险预警", score=0.88),
                CapabilityResult(capability="IoT感知平台", score=0.80),
            ],
        ),
        DepartmentResult(
            department_id=_DEPT_KEJI_ID,
            organization_id=_ORG_ID,
            role="SUPPORT",
            confidence=0.60,
            related_needs=[
                Need(
                    name="基础设施数据治理",
                    confidence=0.70,
                    maturity=NeedMaturity.POTENTIAL,
                ),
            ],
            related_capabilities=[
                CapabilityResult(capability="数据治理", score=0.75),
            ],
        ),
    ],
    capabilities=[
        CapabilityResult(capability="AI风险预警", score=0.88),
        CapabilityResult(capability="IoT感知平台", score=0.80),
        CapabilityResult(capability="数据治理", score=0.75),
    ],
    reason="政策已明确提出基础设施风险监测相关建设任务，存在较强前置数字化建设机会。",
    risks=[],
    recommended_action="建议近期联系相关业务部门确认年度建设计划。",
)

_MINI_REVIEW_FIXTURE = ReviewResult(
    approved=True,
    adjustments=[],
    risk_note="暂无明确采购及预算信息。",
)

FIXTURES: dict[str, BaseModel] = {
    "EVENT_ANALYZE": _EVENT_ANALYZE_FIXTURE,
    "EXPERT_JUDGE": _EXPERT_JUDGE_FIXTURE,
    "MINI_REVIEW": _MINI_REVIEW_FIXTURE,
}
