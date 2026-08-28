import hashlib
import random
import time
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.llm.gateway import LLMGateway
from app.llm.providers.fixtures import FIXTURES
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


def _deterministic_vector(text: str, dimension: int) -> list[float]:
    """Deterministic but non-degenerate -- same text always yields the same
    vector, different texts yield different vectors. Needed so pgvector
    insertion (dimension must match) and TopK ranking in tests aren't
    meaningless against Phase 1's old all-zero stub embedding."""
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dimension)]


class StubLLMGateway(LLMGateway):
    """Deterministic, no-network-calls LLMGateway used in tests and as the
    default provider (LLM_PROVIDER=stub). For task_types in FIXTURES (see
    app/llm/providers/fixtures.py), returns a real, schema-validated canned
    response mirroring the spec §105 demo scenario -- required so the
    Send()-based department fan-out (ADR-0002) has something to iterate over
    in tests. Anything else falls back to the generic type-based filler."""

    def __init__(
        self,
        *,
        fixture_overrides: dict[str, BaseModel] | None = None,
        # Must match the real pgvector column width (app/models/knowledge.py's
        # EMBEDDING_DIMENSION) or vector similarity queries against
        # capability/knowledge_chunk fail with a dimension mismatch -- callers
        # that skip passing settings.embedding_dimension explicitly rely on
        # this default staying in sync with the current migration (0006).
        embedding_dimension: int = 1024,
    ) -> None:
        self._fixtures = {**FIXTURES, **(fixture_overrides or {})}
        self._embedding_dimension = embedding_dimension

    async def structured_generate(
        self, task_type: str, prompt: str, schema: type[T]
    ) -> LLMResult[T]:
        start = time.perf_counter()

        fixture = self._fixtures.get(task_type)
        if fixture is not None and isinstance(fixture, schema):
            instance = schema.model_validate(fixture.model_dump())
        else:
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
        return [
            _deterministic_vector(text, self._embedding_dimension) for text in texts
        ]
