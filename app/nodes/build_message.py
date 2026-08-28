from collections.abc import Awaitable, Callable

from langgraph.types import Command, Send
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import log_node
from app.graph.state import PushBranchPayload
from app.models.push_record import RecipientType
from app.repositories import department_repository, organization_repository

ROLE_LABELS = {
    "LEAD": "可能业务牵头",
    "SUPPORT": "可能技术协同",
}

UNCONFIGURED_OWNER_MARKER = "【暂未配置客户负责人】"


def build_message(
    payload: PushBranchPayload, *, org_name: str | None, dept_name: str | None
) -> str:
    """spec §64's template shape, scoped to exactly one department (Phase 4
    plan design judgment #3 -- each Opportunity is independent, no merging
    even when spec's illustrative example shows multiple departments in one
    message). Not exact spec §65 length control (200-600 chars) -- lists are
    already short at this project's scale; revisit if real content grows."""
    role_label = ROLE_LABELS.get(payload["role"], payload["role"])
    needs = (
        "\n".join(f"• {n['name']}" for n in payload["related_needs"])
        or "（暂无明确需求）"
    )
    capabilities = (
        "\n".join(f"• {c['capability']}" for c in payload["related_capabilities"])
        or "（暂无匹配能力）"
    )
    risks = "\n".join(payload["risks"]) or "暂无明确风险提示"

    lines = [f"🔥 AI发现{payload['level']}级商务机会｜{round(payload['score'])}分"]
    if payload["owner"] is None:
        lines.append(UNCONFIGURED_OWNER_MARKER)
    lines += [
        "",
        "【事件】",
        payload["event_title"],
        "",
        "【AI判断】",
        payload["summary"] or "（无摘要）",
        "",
        "【重点单位】",
        org_name or "未知单位",
        "",
        "【建议部门】",
        f"{dept_name or '未知部门'}｜{role_label}",
        "",
        "【潜在需求】",
        needs,
        "",
        "【我方切入】",
        capabilities,
        "",
        "【当前风险】",
        risks,
        "",
        "【建议动作】",
        payload["recommended_action"] or "（无建议）",
        "",
        "【原始信息】",
        payload["event_source_url"] or "（无原文链接）",
    ]
    return "\n".join(lines)


def make_build_message_node(
    session_factory: async_sessionmaker,
) -> Callable[[PushBranchPayload], Awaitable[Command]]:
    """No RetryPolicy (pure DB lookups + templating, not in spec §71's list)."""

    @log_node("build_message")
    async def build_message_node(payload: PushBranchPayload) -> Command:
        async with session_factory() as session:
            org = await organization_repository.get_by_id(
                session, payload["organization_id"]
            )
            dept = await department_repository.get_by_id(
                session, payload["department_id"]
            )

        message = build_message(
            payload,
            org_name=org.name if org else None,
            dept_name=dept.name if dept else None,
        )

        owner = payload["owner"]
        if owner is not None:
            recipient_type = owner["recipient_type"]
            recipient_id = owner["dingtalk_user_id"]
        else:
            recipient_type = RecipientType.PUBLIC_GROUP
            recipient_id = None

        return Command(
            goto=Send(
                "send_dingtalk",
                {
                    **payload,
                    "message": message,
                    "recipient_type": recipient_type,
                    "recipient_id": recipient_id,
                },
            )
        )

    return build_message_node
