import httpx
import pytest

from app.core.exceptions import LLMError, RAGError, StructuredOutputError
from app.graph.retry import is_transient_error


@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("t"),
        ConnectionError("c"),
        LLMError("llm"),
        StructuredOutputError("bad json"),
        httpx.ConnectError("no route"),
    ],
)
def test_transient_errors_are_retried(exc: Exception) -> None:
    assert is_transient_error(exc) is True


def test_http_5xx_is_transient() -> None:
    response = httpx.Response(503, request=httpx.Request("GET", "http://x"))
    exc = httpx.HTTPStatusError("boom", request=response.request, response=response)
    assert is_transient_error(exc) is True


def test_http_4xx_is_not_transient() -> None:
    response = httpx.Response(404, request=httpx.Request("GET", "http://x"))
    exc = httpx.HTTPStatusError("boom", request=response.request, response=response)
    assert is_transient_error(exc) is False


def test_rag_error_is_not_retried() -> None:
    assert is_transient_error(RAGError("db down")) is False


def test_generic_value_error_is_not_retried() -> None:
    assert is_transient_error(ValueError("business error")) is False
