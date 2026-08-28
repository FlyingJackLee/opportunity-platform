from typing import TypeVar

from pydantic import BaseModel

from app.llm.gateway import LLMGateway
from app.schemas.llm import LLMResult

T = TypeVar("T", bound=BaseModel)


class CompositeLLMGateway(LLMGateway):
    """Routes structured_generate and embed to independently-configured
    backends (LLM_PROVIDER vs EMBEDDING_PROVIDER, see ADR-0004) -- e.g. a
    chat-only vendor like DeepSeek (no embeddings endpoint) paired with a
    separate embedding backend, without either axis knowing the other
    exists. Node/knowledge call sites keep depending on the single
    LLMGateway interface from spec §75; only app/main.py's wiring knows two
    backends are involved."""

    def __init__(self, *, chat: LLMGateway, embedding: LLMGateway) -> None:
        self._chat = chat
        self._embedding = embedding

    async def structured_generate(
        self, task_type: str, prompt: str, schema: type[T]
    ) -> LLMResult[T]:
        return await self._chat.structured_generate(task_type, prompt, schema)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._embedding.embed(texts)
