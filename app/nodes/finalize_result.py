import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.models.event import EventStatus
from app.repositories import event_repository, expert_run_repository

UNKNOWN = "UNKNOWN"


def make_finalize_result_node(
    session_factory: async_sessionmaker,
) -> Callable[[OpportunityState], Awaitable[dict]]:
    """Joins calculate_score's fan-out results back against expert_result,
    persists the ExpertRun, marks the Event ANALYZED. Top-level score/level/
    confidence is the full triple from whichever department scored highest --
    not three independently-maxed fields (see CONTEXT.md's FinalResult entry)."""

    @log_node("finalize_result")
    async def finalize_result(state: OpportunityState) -> dict:
        expert_result = state["expert_result"]
        original_by_id = {
            d["department_id"]: d for d in expert_result.get("departments", [])
        }

        department_entries = []
        for branch in state["departments"]:
            original = original_by_id.get(branch["department_id"])
            department_entries.append(
                {
                    "department_id": branch["department_id"],
                    "organization_id": branch["organization_id"],
                    "role": original["role"] if original else UNKNOWN,
                    "related_needs": original.get("related_needs", [])
                    if original
                    else [],
                    "related_capabilities": original.get("related_capabilities", [])
                    if original
                    else [],
                    "score": branch["score"],
                    "level": branch["level"],
                    "confidence": branch["confidence"],
                }
            )

        top_branch = max(department_entries, key=lambda d: d["score"])

        final_result = {
            "event_id": state["event"]["id"],
            "score": top_branch["score"],
            "level": top_branch["level"],
            "confidence": top_branch["confidence"],
            "summary": expert_result.get("reason", ""),
            "needs": expert_result.get("needs", []),
            "organizations": expert_result.get("organizations", []),
            "departments": department_entries,
            "capabilities": expert_result.get("capabilities", []),
            "risks": expert_result.get("risks", []),
            "recommended_action": expert_result.get("recommended_action", ""),
        }

        async with session_factory() as session:
            await expert_run_repository.complete_run(
                session,
                uuid.UUID(state["run_id"]),
                score=top_branch["score"],
                level=top_branch["level"],
                confidence=top_branch["confidence"],
                result_json=final_result,
                model_version=state.get("model_version"),
                event_prompt_version=state.get("event_prompt_version"),
                judge_prompt_version=state.get("judge_prompt_version"),
                review_prompt_version=state.get("review_prompt_version"),
            )
            await event_repository.set_event_status(
                session, uuid.UUID(state["event"]["id"]), EventStatus.ANALYZED
            )

        return {
            "final_result": final_result,
            "score": top_branch["score"],
            "level": top_branch["level"],
            "confidence": top_branch["confidence"],
            "status": "COMPLETED",
        }

    return finalize_result
