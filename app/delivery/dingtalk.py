"""spec §63: DingTalk custom-robot ("自定义机器人") webhook adapter.

Verified against DingTalk's current open-platform docs for 自定义机器人接入:
the signature is base64(HMAC-SHA256(secret, f"{timestamp}\\n{secret}")),
URL-encoded and appended as `timestamp`/`sign` query params. This robot type
is group-only -- it cannot send a true 1:1 direct message (that needs a
separate, heavier "工作通知" enterprise-app integration, out of scope here).
`at.atUserIds` lets us @-mention a specific member of the bound group, which
is how CONTEXT.md's "Customer Owner" gets notified (design judgment #4 in the
Phase 4 plan)."""

import base64
import hashlib
import hmac
import time
import urllib.parse

import httpx

from app.delivery.channel import PushResult

REQUEST_TIMEOUT_SECONDS = 10.0


def _build_signed_url(webhook_url: str, webhook_secret: str | None) -> str:
    if not webhook_secret:
        return webhook_url
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{webhook_secret}"
    hmac_code = hmac.new(
        webhook_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"


class DingTalkAdapter:
    """Real webhook implementation. A DingTalk-level business rejection
    (errcode != 0, e.g. an expired/invalid signature) is a normal return
    value (PushResult(status="FAILED")), never an exception -- spec §72:
    business errors don't retry. Only transport-level failures (timeout,
    connection error, 5xx) propagate, for RetryPolicy (spec §71) to catch."""

    def __init__(self, *, timeout: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send_text(
        self,
        *,
        webhook_url: str,
        webhook_secret: str | None,
        content: str,
        at_user_ids: list[str] | None = None,
        is_at_all: bool = False,
    ) -> PushResult:
        url = _build_signed_url(webhook_url, webhook_secret)
        payload = {
            "msgtype": "text",
            "text": {"content": content},
            "at": {"atUserIds": at_user_ids or [], "isAtAll": is_at_all},
        }
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("errcode", 0) == 0:
            return PushResult(status="SENT", raw_response=body)
        return PushResult(
            status="FAILED",
            error=body.get("errmsg", "unknown error"),
            raw_response=body,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
