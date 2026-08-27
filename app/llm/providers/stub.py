import time
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.llm.gateway import LLMGateway
from app.schemas.llm import LLMResult, TokenUsage

T = TypeVar("T", bound=BaseModel)

_PLACEHOLDER_BY_TYPE: dict[type, Any] = {
    str: "stub",
    int: 0,
    float: 0.0,
    bool: False,
    list: [],
    dict: {},
}


def _stub_value(annotation: Any) -> Any:
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        return _PLACEHOLDER_BY_TYPE.get(origin, None)
    return _PLACEHOLDER_BY_TYPE.get(annotation, None)


class StubLLMGateway(LLMGateway):
    """Deterministic, no-network-calls LLMGateway used in tests and as the
    default provider (LLM_PROVIDER=stub) — Phase 1's acceptance test runs
    against this, no real API key required."""

    async def structured_generate(
        self, task_type: str, prompt: str, schema: type[T]
    ) -> LLMResult[T]:
        start = time.perf_counter()
        values: dict[str, Any] = {}
        for name, field in schema.model_fields.items():
            if field.default is not PydanticUndefined:
                values[name] = field.default
            elif field.default_factory is not None:
                values[name] = field.default_factory()  # type: ignore[call-arg]
            else:
                values[name] = _stub_value(field.annotation)
        instance = schema.model_validate(values)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResult(
            data=instance,
            model="stub-model",
            usage=TokenUsage(input_tokens=len(prompt.split()), output_tokens=0),
            latency_ms=latency_ms,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]
