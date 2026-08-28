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
    """Real provider against any OpenAI-compatible chat-completions API, using
    response_format=json_object rather than the newer response_format=
    json_schema strict mode -- verified against a live DeepSeek key that the
    latter is a no-go for provider-agnosticism (spec §75): DeepSeek's own API
    docs only list `text`/`json_object` for response_format, not
    `json_schema` (some third-party relays bolt it on, but that's not
    something this gateway can assume from a base_url alone). json_object
    only guarantees syntactically valid JSON, not which keys/enum values are
    used, so the target schema is serialized into the prompt itself instead
    -- portable across any vendor that supports json_object, no per-vendor
    capability branching needed."""

    def __init__(
        self, *, api_key: str, model: str, base_url: str, timeout: float = 120.0
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
        # response_format=json_object requires the word "json" to appear
        # somewhere in the prompt (OpenAI/DeepSeek both 400 otherwise) --
        # appended rather than relying on every prompt_template author to
        # remember it. The schema itself is appended too: prompt_template
        # content (app/repositories/prompt_repository.py) is prose describing
        # WHAT to analyze, never the JSON field names/enum values to emit --
        # without this, models return their own free-form (often
        # Chinese-language) keys that fail Pydantic validation every time.
        json_prompt = (
            f"{prompt}\n\n"
            "请仅输出一个合法的 JSON 对象（valid JSON object），不要包含任何额外说明文字、"
            "不要使用 markdown 代码块。JSON 的字段名、结构和取值范围必须严格符合以下 "
            "JSON Schema（字段名用英文，按 schema 里的 enum 取值，不要翻译成中文）：\n"
            f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
        )
        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": json_prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"{task_type}: LLM request failed: {exc}; body={exc.response.text[:1000]}"
            ) from exc
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
