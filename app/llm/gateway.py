import abc
from typing import TypeVar

from pydantic import BaseModel

from app.schemas.llm import LLMResult

T = TypeVar("T", bound=BaseModel)


class LLMGateway(abc.ABC):
    """Provider-agnostic LLM access (spec §75) — no node may depend directly on
    a specific model vendor."""

    @abc.abstractmethod
    async def structured_generate(
        self, task_type: str, prompt: str, schema: type[T]
    ) -> LLMResult[T]: ...

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
