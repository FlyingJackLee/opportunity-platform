from pydantic import BaseModel

from app.llm.gateway import LLMGateway
from app.llm.providers.stub import StubLLMGateway


class _Schema(BaseModel):
    name: str
    confidence: float
    tags: list[str]


async def test_stub_satisfies_llm_gateway_interface() -> None:
    gateway: LLMGateway = StubLLMGateway()
    assert isinstance(gateway, LLMGateway)


async def test_structured_generate_returns_well_formed_result() -> None:
    gateway = StubLLMGateway()

    result = await gateway.structured_generate(
        task_type="TEST", prompt="hello world", schema=_Schema
    )

    assert isinstance(result.data, _Schema)
    assert result.model == "stub-model"
    assert result.usage.input_tokens == 2
    assert result.usage.output_tokens == 0
    assert result.latency_ms >= 0


async def test_structured_generate_is_deterministic() -> None:
    gateway = StubLLMGateway()

    first = await gateway.structured_generate(
        task_type="TEST", prompt="a b c", schema=_Schema
    )
    second = await gateway.structured_generate(
        task_type="TEST", prompt="a b c", schema=_Schema
    )

    assert first.data == second.data


async def test_embed_returns_one_vector_per_text() -> None:
    gateway = StubLLMGateway()

    vectors = await gateway.embed(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(isinstance(v, list) for v in vectors)
