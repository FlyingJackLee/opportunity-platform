import json
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.core.exceptions import LLMError, StructuredOutputError
from app.llm.gateway import LLMGateway
from app.schemas.llm import LLMResult, TokenUsage

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleLLMGateway(LLMGateway):
    """Real provider skeleton against any OpenAI-compatible chat-completions API
    (JSON mode for structured output). Not exercised against a live key in
    Phase 1 — proves the LLMGateway interface isn't stub-only."""

    def __init__(
        self, *, api_key: str, model: str, base_url: str, timeout: float = 30.0
    ) -> None:
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def structured_generate(
        self, task_type: str, prompt: str, schema: type[T]
    ) -> LLMResult[T]:
        start = time.perf_counter()
        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"{task_type}: LLM request failed: {exc}") from exc

        body = response.json()
        content = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})

        try:
            instance = schema.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValueError) as exc:
            raise StructuredOutputError(
                f"{task_type}: failed to parse structured output: {exc}"
            ) from exc

        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResult(
            data=instance,
            model=body.get("model", self._model),
            usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            ),
            latency_ms=latency_ms,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.post(
                "/embeddings", json={"model": self._model, "input": texts}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"embed: request failed: {exc}") from exc
        body = response.json()
        return [item["embedding"] for item in body["data"]]
