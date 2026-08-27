from app.llm.gateway import LLMGateway


async def embed_query(gateway: LLMGateway, text: str) -> list[float]:
    vectors = await gateway.embed([text])
    return vectors[0]
