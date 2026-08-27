from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import DepartmentBranchState, ScoreFanoutInput
from app.repositories.score_config_repository import (
    COMPANY_CAPABILITY,
    DEPARTMENT_MATCH,
    EVENT_RELEVANCE,
    NEED_CLARITY,
    ORGANIZATION_MATCH,
    PROCUREMENT_SIGNAL,
    PROJECT_SIGNAL,
    get_weights,
)

# Design judgment #4 (Phase 2 plan): spec §47 only gives the 7 weights, not
# these per-component formulas.
MATURITY_WEIGHT = {
    "CONCEPT": 0.2,
    "POTENTIAL": 0.4,
    "EXPLICIT": 0.7,
    "PROJECT": 0.85,
    "PROCUREMENT": 1.0,
}
SIGNAL_WEIGHT = {"UNKNOWN": 0.0, "LOW": 0.33, "MEDIUM": 0.66, "HIGH": 1.0}


def level_for_score(score: float) -> str:
    """spec §48 -- Code's job, never the LLM's (spec §46)."""
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    return "WATCH"


def _need_clarity(related_needs: list[dict]) -> float:
    if not related_needs:
        return 0.0
    values = [
        n["confidence"] * MATURITY_WEIGHT.get(n["maturity"], 0.0) for n in related_needs
    ]
    return sum(values) / len(values)


def _company_capability(related_capabilities: list[dict]) -> float:
    if not related_capabilities:
        return 0.0
    return sum(c["score"] for c in related_capabilities) / len(related_capabilities)


def make_calculate_score_node(
    session_factory: async_sessionmaker,
) -> Callable[[ScoreFanoutInput], Awaitable[dict]]:
    """The Send("calculate_score", ...) target -- operates on one department's
    ScoreFanoutInput slice, not the full OpportunityState (ADR-0002). No
    RetryPolicy: pure Code, not in spec §71's retry-eligible node list."""

    @log_node("calculate_score")
    async def calculate_score(payload: ScoreFanoutInput) -> dict:
        async with session_factory() as session:
            weights = await get_weights(session)

        need_clarity = _need_clarity(payload["related_needs"])
        company_capability = _company_capability(payload["related_capabilities"])
        components = {
            EVENT_RELEVANCE: payload["event_relevance"],
            NEED_CLARITY: need_clarity,
            ORGANIZATION_MATCH: payload["organization_score"],
            DEPARTMENT_MATCH: payload["department_confidence"],
            COMPANY_CAPABILITY: company_capability,
            PROJECT_SIGNAL: SIGNAL_WEIGHT.get(payload["project_signal"], 0.0),
            PROCUREMENT_SIGNAL: SIGNAL_WEIGHT.get(payload["procurement_signal"], 0.0),
        }
        score = round(100 * sum(components[key] * weights[key] for key in components))
        level = level_for_score(score)

        need_confidences = [n["confidence"] for n in payload["related_needs"]]
        mean_need_confidence = (
            sum(need_confidences) / len(need_confidences) if need_confidences else 0.0
        )
        confidence = (
            payload["organization_score"]
            + payload["department_confidence"]
            + mean_need_confidence
        ) / 3

        branch: DepartmentBranchState = {
            "department_id": payload["department_id"],
            "organization_id": payload["organization_id"],
            "score": float(score),
            "level": level,
            "confidence": confidence,
            "should_push": False,
            "owner": None,
            "push_result": None,
            "error": None,
        }
        return {"departments": [branch]}

    return calculate_score
