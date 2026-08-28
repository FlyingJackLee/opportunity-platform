import base64
import hashlib
import hmac

import pytest

from app.delivery.dingtalk import DingTalkAdapter, _build_signed_url


def test_signature_matches_known_vector() -> None:
    secret = "SEC_test_secret"
    url = _build_signed_url(
        "https://oapi.dingtalk.com/robot/send?access_token=abc", secret
    )

    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    timestamp = query["timestamp"][0]
    sign = query["sign"][0]

    # recompute independently, per DingTalk's documented algorithm.
    # parse_qs already percent-decodes, so compare against the plain base64
    # string, not a re-quoted one.
    string_to_sign = f"{timestamp}\n{secret}"
    expected_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    expected_sign = base64.b64encode(expected_code).decode()
    assert sign == expected_sign


def test_no_secret_leaves_url_unsigned() -> None:
    url = _build_signed_url(
        "https://oapi.dingtalk.com/robot/send?access_token=abc", None
    )
    assert url == "https://oapi.dingtalk.com/robot/send?access_token=abc"


async def test_send_text_success(local_dingtalk_server) -> None:
    base_url, log = local_dingtalk_server
    adapter = DingTalkAdapter()
    try:
        result = await adapter.send_text(
            webhook_url=f"{base_url}/robot/send",
            webhook_secret="my-secret",
            content="test message",
            at_user_ids=["user1"],
        )
    finally:
        await adapter.aclose()

    assert result.status == "SENT"
    assert len(log.requests) == 1
    req = log.requests[0]
    assert req["path"] == "/robot/send"
    assert "sign" in req["query"]
    assert "timestamp" in req["query"]
    assert req["body"]["text"]["content"] == "test message"
    assert req["body"]["at"]["atUserIds"] == ["user1"]


async def test_send_text_business_failure_is_not_an_exception(
    local_dingtalk_server,
) -> None:
    base_url, log = local_dingtalk_server
    log.responses["/robot/send"] = {
        "errcode": 300001,
        "errmsg": "keywords not in content",
    }

    adapter = DingTalkAdapter()
    try:
        result = await adapter.send_text(
            webhook_url=f"{base_url}/robot/send",
            webhook_secret=None,
            content="no keyword here",
        )
    finally:
        await adapter.aclose()

    assert result.status == "FAILED"
    assert result.error == "keywords not in content"


async def test_send_text_transport_failure_raises() -> None:
    adapter = DingTalkAdapter(timeout=2.0)
    try:
        with pytest.raises(Exception):  # noqa: B017 -- any transport-level httpx error is fine here
            await adapter.send_text(
                webhook_url="http://127.0.0.1:1/unreachable",
                webhook_secret=None,
                content="x",
            )
    finally:
        await adapter.aclose()
