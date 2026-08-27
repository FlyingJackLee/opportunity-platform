from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate

logger = structlog.get_logger()


@dataclass
class ActivePrompt:
    content: str
    version: str


DEFAULT_PROMPTS: dict[str, ActivePrompt] = {
    "EVENT_ANALYZE": ActivePrompt(
        version="fallback-v0",
        content=(
            "你正在分析一条公开信息，目标是理解事件本身，而不是进行商务判断（spec §25）。\n"
            "只分析事件原文明确表达的内容。不得：\n"
            "- 判断客户\n"
            "- 推荐部门\n"
            "- 推测公司能力\n"
            "- 将政策目标视为采购需求\n"
            "输出事件类型、地区、行业、主题、任务、涉及对象，以及项目/预算/采购信号（信息不足时用 UNKNOWN）。"
        ),
    ),
    "EXPERT_JUDGE": ActivePrompt(
        version="fallback-v0",
        content=(
            "你是行业专家，基于事件分析结果和检索到的行业知识、组织候选、公司能力，回答：\n"
            "有没有机会？可能需要什么？哪些单位？哪些部门？谁可能牵头？我们能提供什么？下一步做什么？\n"
            "强约束：\n"
            "- 不得创建不存在于候选列表的部门\n"
            "- 不得创建不存在于公司能力库的能力\n"
            "- 不得将 POTENTIAL Need 说成明确项目\n"
            "- 不得将 Policy Signal 直接判断为 Procurement\n"
            "- 信息不足时允许 UNKNOWN\n"
            "每个识别出的部门必须给出它自己的 related_needs 和 related_capabilities，"
            "不同部门可以对应不同的需求和能力组合。"
        ),
    ),
    "MINI_REVIEW": ActivePrompt(
        version="fallback-v0",
        content=(
            "只检查以下几点，不做完整的重新研判：\n"
            "- 是否把潜在需求说成明确采购？\n"
            "- 是否出现不存在的单位/部门？\n"
            "- 是否出现公司不存在的能力？\n"
            "- 部门职责解释是否合理？\n"
            "- 是否存在明显过度判断？"
        ),
    ),
}


async def get_active_prompt(session: AsyncSession, task_type: str) -> ActivePrompt:
    """DB row with enabled=True wins; falls back to a hardcoded default
    (logged as a warning) so the API works before an operator has populated
    prompt_template -- scripts/seed_phase2.py is still the intended primary
    source."""
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.task_type == task_type, PromptTemplate.enabled.is_(True))
        .order_by(PromptTemplate.created_at.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).scalars().first()
    if row is not None:
        return ActivePrompt(content=row.content, version=row.version)

    logger.warning("prompt_fallback_used", task_type=task_type)
    fallback = DEFAULT_PROMPTS.get(task_type)
    if fallback is None:
        raise LookupError(
            f"no prompt configured or fallback defined for task_type={task_type}"
        )
    return fallback
