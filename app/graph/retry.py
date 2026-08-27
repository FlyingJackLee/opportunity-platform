import httpx

from app.core.exceptions import LLMError, StructuredOutputError


def is_transient_error(exc: Exception) -> bool:
    """spec §71: only retry Timeout/ConnectionError/HTTP 5xx/LLM transient
    errors -- business errors (spec §72, e.g. "can't find owner") must not
    retry. StructuredOutputError is included: a malformed-JSON response from
    a non-deterministic LLM is plausibly transient, unlike a hard business
    error. RAGError is deliberately excluded -- a DB query failure more often
    indicates a real bug than flakiness."""
    if isinstance(
        exc,
        httpx.TimeoutException | httpx.ConnectError | TimeoutError | ConnectionError,
    ):
        return True
    if isinstance(exc, LLMError | StructuredOutputError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return False
