"""spec §63's delivery abstraction -- a channel-agnostic interface so nodes
never depend on DingTalk specifics directly, mirroring app/llm/gateway.py's
LLMGateway pattern."""

from typing import Literal, Protocol

from pydantic import BaseModel


class PushResult(BaseModel):
    status: Literal["SENT", "FAILED"]
    error: str | None = None
    raw_response: dict | None = None


class DeliveryChannel(Protocol):
    async def send_text(
        self,
        *,
        webhook_url: str,
        webhook_secret: str | None,
        content: str,
        at_user_ids: list[str] | None = None,
        is_at_all: bool = False,
    ) -> PushResult: ...
