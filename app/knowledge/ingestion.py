import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embedding import embed_query
from app.llm.gateway import LLMGateway
from app.models.capability import Capability
from app.models.knowledge import KnowledgeChunk


async def ingest_knowledge_chunk(
    session: AsyncSession,
    gateway: LLMGateway,
    *,
    id: uuid.UUID,
    knowledge_type: str,
    title: str,
    content: str,
    industry: str | None = None,
    region: str | None = None,
    topic: str | None = None,
    metadata: dict | None = None,
    status: str = "ACTIVE",
) -> KnowledgeChunk:
    """Computes the embedding and upserts by id (session.merge -- idempotent,
    used by scripts/seed_phase2.py so re-running the seed script is safe)."""
    embedding = await embed_query(gateway, f"{title} {content}")
    chunk = KnowledgeChunk(
        id=id,
        knowledge_type=knowledge_type,
        title=title,
        content=content,
        industry=industry,
        region=region,
        topic=topic,
        embedding=embedding,
        metadata_=metadata,
        status=status,
    )
    return await session.merge(chunk)


async def ingest_capability(
    session: AsyncSession,
    gateway: LLMGateway,
    *,
    id: uuid.UUID,
    name: str,
    scenarios: list[str] | None = None,
    industries: list[str] | None = None,
    solutions: dict | None = None,
    cases: dict | None = None,
    description: str | None = None,
    status: str = "ACTIVE",
) -> Capability:
    embedding = await embed_query(
        gateway, f"{name} {' '.join(scenarios or [])} {description or ''}"
    )
    capability = Capability(
        id=id,
        name=name,
        scenarios=scenarios,
        industries=industries,
        solutions=solutions,
        cases=cases,
        description=description,
        embedding=embedding,
        status=status,
    )
    return await session.merge(capability)
