import json
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway
from app.repositories.capability_repository import capability_exists
from app.repositories.department_repository import department_exists
from app.repositories.organization_repository import organization_exists
from app.repositories.prompt_repository import get_active_prompt
from app.schemas.review import ReviewResult

CONFIDENCE_DAMPENING_FACTOR = 0.7


async def _find_fabricated_references(
    session_factory: async_sessionmaker, expert_result: dict
) -> list[str]:
    """spec §51's fabrication checks, run unconditionally against the full DB
    (not just the candidate list originally shown to expert_judge -- simpler,
    more robust, at the cost of not catching a real-but-off-topic citation)."""
    problems: list[str] = []
    async with session_factory() as session:
        for org in expert_result.get("organizations", []):
            if not await organization_exists(session, org["organization_id"]):
                problems.append(f"unknown organization_id={org['organization_id']}")
        for dept in expert_result.get("departments", []):
            if not await department_exists(session, dept["department_id"]):
                problems.append(f"unknown department_id={dept['department_id']}")
            if not await organization_exists(session, dept["organization_id"]):
                problems.append(f"unknown organization_id={dept['organization_id']}")
            for cap in dept.get("related_capabilities", []):
                if not await capability_exists(session, cap["capability"]):
                    problems.append(f"unknown capability={cap['capability']}")
        for cap in expert_result.get("capabilities", []):
            if not await capability_exists(session, cap["capability"]):
                problems.append(f"unknown capability={cap['capability']}")
    return problems


def make_mini_review_node(
    gateway: LLMGateway, session_factory: async_sessionmaker
) -> Callable[[OpportunityState], Awaitable[dict]]:
    """spec §50-53: one lightweight review pass, global (not per department --
    it checks cross-department validity like fabricated orgs/departments,
    which needs the full picture). Code, not the LLM, decides the consequence
    of a failed review (spec §53): dampen confidence + append a risk note.
    Runs *before* the calculate_score Send() fan-out (ADR-0002)."""

    @log_node("mini_review")
    async def mini_review(state: OpportunityState) -> dict:
        async with session_factory() as session:
            prompt = await get_active_prompt(session, "MINI_REVIEW")

        expert_result = dict(state["expert_result"])
        full_prompt = f"{prompt.content}\n\n【Expert 研判结果】\n{json.dumps(expert_result, ensure_ascii=False)}"
        result = await gateway.structured_generate(
            task_type="MINI_REVIEW", prompt=full_prompt, schema=ReviewResult
        )
        review = result.data

        fabricated = await _find_fabricated_references(session_factory, expert_result)
        approved = review.approved and not fabricated

        if not approved:
            expert_result["departments"] = [
                {**dept, "confidence": dept["confidence"] * CONFIDENCE_DAMPENING_FACTOR}
                for dept in expert_result.get("departments", [])
            ]
            risk_notes = [n for n in [review.risk_note] if n] + [
                f"审核发现: {p}" for p in fabricated
            ]
            expert_result["risks"] = [*expert_result.get("risks", []), *risk_notes]

        return {
            "expert_result": expert_result,
            "review_result": {
                "approved": approved,
                "adjustments": review.adjustments,
                "risk_note": review.risk_note,
                "fabricated_references": fabricated,
            },
            "review_prompt_version": prompt.version,
        }

    return mini_review
