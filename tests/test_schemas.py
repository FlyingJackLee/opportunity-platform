import pytest
from pydantic import ValidationError

from app.schemas.analysis import EventAnalysis, EventType
from app.schemas.expert import DepartmentResult, ExpertResult, Need, NeedMaturity
from app.schemas.final_result import FinalResult
from app.schemas.review import ReviewResult


def test_event_analysis_requires_event_type_and_region() -> None:
    with pytest.raises(ValidationError):
        EventAnalysis.model_validate({})


def test_event_analysis_minimal_valid() -> None:
    analysis = EventAnalysis(event_type=EventType.POLICY, region="重庆市")
    assert analysis.industry == []
    assert analysis.signals.project_signal == "UNKNOWN"


def test_expert_result_has_no_stage_field() -> None:
    assert "stage" not in ExpertResult.model_fields


def test_department_result_carries_organization_id_and_related_capabilities() -> None:
    dept = DepartmentResult(
        department_id="d1",
        organization_id="o1",
        role="LEAD",
        confidence=0.8,
        related_needs=[Need(name="n", confidence=0.5, maturity=NeedMaturity.POTENTIAL)],
    )
    assert dept.organization_id == "o1"
    assert dept.related_capabilities == []


def test_review_result_defaults() -> None:
    review = ReviewResult(approved=True)
    assert review.adjustments == []
    assert review.risk_note == ""


def test_final_result_has_no_stage_field() -> None:
    assert "stage" not in FinalResult.model_fields


def test_final_result_requires_event_id_and_score() -> None:
    with pytest.raises(ValidationError):
        FinalResult.model_validate({})
