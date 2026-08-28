"""Default channel when no real webhook is configured (Settings.dingtalk_
webhook_url unset) -- records calls, always returns SENT. Same "don't invent
a real destination" posture as scripts/seed_phase3.py's placeholder source:
a real webhook gets wired in later via config, no code changes needed."""

from app.delivery.channel import PushResult


class RecordingDeliveryChannel:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def send_text(
        self,
        *,
        webhook_url: str,
        webhook_secret: str | None,
        content: str,
        at_user_ids: list[str] | None = None,
        is_at_all: bool = False,
    ) -> PushResult:
        self.calls.append(
            {
                "webhook_url": webhook_url,
                "content": content,
                "at_user_ids": at_user_ids or [],
                "is_at_all": is_at_all,
            }
        )
        return PushResult(status="SENT")
