from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class LLMResult(BaseModel, Generic[T]):  # noqa: UP046 -- PEP 695 type params
    # have known rough edges with Pydantic v2's generic model machinery;
    # Generic[T] is the safer, standard way to write a generic BaseModel here.
    """Wraps LLMGateway.structured_generate's return value with the metadata
    spec §87 (logging) and §88 (cost tracking) need at the call site — a
    deliberate deviation from spec §75's bare-value pseudocode, flagged in the
    Phase 1 plan for approval."""

    data: T
    model: str
    usage: TokenUsage
    latency_ms: float
