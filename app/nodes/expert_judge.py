import json
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import OpportunityState
from app.llm.gateway import LLMGateway
from app.repositories.prompt_repository import get_active_prompt
from app.schemas.expert import ExpertResult


def make_expert_judge_node(
    gateway: LLMGateway, session_factory: async_sessionmaker
) -> Callable[[OpportunityState], Awaitable[dict]]:
    """spec §40-43: the single most core LLM node."""

    @log_node("expert_judge")
    async def expert_judge(state: OpportunityState) -> dict:
        async with session_factory() as session:
            prompt = await get_active_prompt(session, "EXPERT_JUDGE")

        full_prompt = (
            f"{prompt.content}\n\n"
            f"【事件分析】\n{json.dumps(state['event_analysis'], ensure_ascii=False)}\n\n"
            f"【行业知识候选】\n{json.dumps(state['industry_context'], ensure_ascii=False)}\n\n"
            f"【组织/部门候选】\n{json.dumps(state['organization_context'], ensure_ascii=False)}\n\n"
            f"【公司能力候选】\n{json.dumps(state['capability_context'], ensure_ascii=False)}"
        )
        result = await gateway.structured_generate(
            task_type="EXPERT_JUDGE", prompt=full_prompt, schema=ExpertResult
        )
        return {
            "expert_result": result.data.model_dump(mode="json"),
            "judge_prompt_version": prompt.version,
            "model_version": result.model,
        }

    return expert_judge
