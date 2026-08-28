from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from langgraph.types import Command, Send

from app.core.config import Settings
from app.core.logging import log_node
from app.delivery.channel import DeliveryChannel
from app.graph.state import PushBranchPayload
from app.models.push_record import RecipientType


def make_send_dingtalk_node(
    channel: DeliveryChannel, settings: Settings
) -> Callable[[PushBranchPayload], Awaitable[Command]]:
    """RetryPolicy attached at graph-registration time (spec §71 explicitly
    lists send_dingtalk). A DingTalk business-level rejection comes back as a
    normal PushResult(status="FAILED") from the channel -- never raised, so
    it never touches the retry policy (spec §72: business errors don't
    retry). Only transport-level exceptions propagate here."""

    @log_node("send_dingtalk")
    async def send_dingtalk(payload: PushBranchPayload) -> Command:
        if payload["recipient_type"] == RecipientType.PUBLIC_GROUP:
            webhook_url = settings.dingtalk_public_group_webhook_url
            webhook_secret = settings.dingtalk_public_group_webhook_secret
            at_user_ids: list[str] = []
        else:
            webhook_url = settings.dingtalk_webhook_url
            webhook_secret = settings.dingtalk_webhook_secret
            at_user_ids = [payload["recipient_id"]] if payload["recipient_id"] else []

        result = await channel.send_text(
            webhook_url=webhook_url or "",
            webhook_secret=webhook_secret,
            content=payload["message"],
            at_user_ids=at_user_ids,
        )

        push_result = result.model_dump(mode="json")
        push_result["sent_at"] = datetime.now(UTC).isoformat()
        return Command(goto=Send("archive", {**payload, "push_result": push_result}))

    return send_dingtalk
