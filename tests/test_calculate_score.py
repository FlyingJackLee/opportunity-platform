import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.nodes.calculate_score import (
    _company_capability,
    _need_clarity,
    level_for_score,
    make_calculate_score_node,
)


@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (100, "A"),
        (80, "A"),
        (79.9, "B"),
        (65, "B"),
        (64.9, "C"),
        (50, "C"),
        (49.9, "WATCH"),
        (0, "WATCH"),
    ],
)
def test_level_for_score_boundaries(score: float, expected_level: str) -> None:
    assert level_for_score(score) == expected_level


def test_need_clarity_empty_is_zero() -> None:
    assert _need_clarity([]) == 0.0


def test_need_clarity_weights_by_maturity() -> None:
    needs = [
        {"confidence": 1.0, "maturity": "PROCUREMENT"},
        {"confidence": 1.0, "maturity": "CONCEPT"},
    ]
    # (1.0*1.0 + 1.0*0.2) / 2
    assert _need_clarity(needs) == pytest.approx(0.6)


def test_company_capability_empty_is_zero() -> None:
    assert _company_capability([]) == 0.0


def test_company_capability_is_mean_of_scores() -> None:
    caps = [{"capability": "a", "score": 0.8}, {"capability": "b", "score": 0.4}]
    assert _company_capability(caps) == pytest.approx(0.6)


@pytest.fixture
def session_factory():
    engine = create_async_engine(get_settings().database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.usefixtures("_test_database")
async def test_calculate_score_node_uses_seeded_weights(session_factory) -> None:
    node = make_calculate_score_node(session_factory)
    payload = {
        "run_id": "r1",
        "department_id": "dep-1",
        "organization_id": "org-1",
        "department_confidence": 1.0,
        "organization_score": 1.0,
        "related_needs": [{"name": "n", "confidence": 1.0, "maturity": "PROCUREMENT"}],
        "related_capabilities": [{"capability": "c", "score": 1.0}],
        "event_relevance": 1.0,
        "project_signal": "HIGH",
        "procurement_signal": "HIGH",
    }
    result = await node(payload)
    branch = result["departments"][0]
    # every component maxed out and spec §47's weights sum to 1.0 -> score == 100
    assert branch["score"] == 100.0
    assert branch["level"] == "A"
    assert branch["department_id"] == "dep-1"
