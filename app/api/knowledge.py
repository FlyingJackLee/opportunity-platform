import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.knowledge.ingestion import ingest_knowledge_chunk
from app.repositories import knowledge_repository
from app.schemas.knowledge import (
    KnowledgeChunkCreate,
    KnowledgeChunkRead,
    KnowledgeChunkUpdate,
)

router = APIRouter(prefix="/api/v1/knowledge-chunks", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeChunkRead])
async def list_knowledge_chunks_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgeChunkRead]:
    chunks = await knowledge_repository.list_all(session)
    return [KnowledgeChunkRead.model_validate(c) for c in chunks]


@router.get("/{chunk_id}", response_model=KnowledgeChunkRead)
async def get_knowledge_chunk_endpoint(
    chunk_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeChunkRead:
    chunk = await knowledge_repository.get(session, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="knowledge chunk not found")
    return KnowledgeChunkRead.model_validate(chunk)


@router.post("", response_model=KnowledgeChunkRead)
async def create_knowledge_chunk_endpoint(
    payload: KnowledgeChunkCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeChunkRead:
    chunk = await ingest_knowledge_chunk(
        session,
        request.app.state.llm_gateway,
        id=uuid.uuid4(),
        **payload.model_dump(),
    )
    await session.commit()
    return KnowledgeChunkRead.model_validate(chunk)


@router.patch("/{chunk_id}", response_model=KnowledgeChunkRead)
async def update_knowledge_chunk_endpoint(
    chunk_id: uuid.UUID,
    payload: KnowledgeChunkUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeChunkRead:
    """ingest_knowledge_chunk is a full upsert -- merge the patch onto the
    existing row's fields before re-ingesting (recomputes the embedding even
    if only e.g. `topic` changed, which is wasteful but harmless/idempotent;
    not worth a separate partial-update code path for a one-期 admin tool)."""
    existing = await knowledge_repository.get(session, chunk_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="knowledge chunk not found")
    updates = payload.model_dump(exclude_unset=True)
    chunk = await ingest_knowledge_chunk(
        session,
        request.app.state.llm_gateway,
        id=chunk_id,
        knowledge_type=existing.knowledge_type,
        title=updates.get("title", existing.title),
        content=updates.get("content", existing.content),
        industry=updates.get("industry", existing.industry),
        region=updates.get("region", existing.region),
        topic=updates.get("topic", existing.topic),
        metadata=updates.get("metadata", existing.metadata_),
        status=existing.status,
    )
    await session.commit()
    return KnowledgeChunkRead.model_validate(chunk)


@router.post("/{chunk_id}/deactivate", response_model=KnowledgeChunkRead)
async def deactivate_knowledge_chunk_endpoint(
    chunk_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeChunkRead:
    chunk = await knowledge_repository.set_status(session, chunk_id, "INACTIVE")
    if chunk is None:
        raise HTTPException(status_code=404, detail="knowledge chunk not found")
    return KnowledgeChunkRead.model_validate(chunk)


@router.post("/{chunk_id}/activate", response_model=KnowledgeChunkRead)
async def activate_knowledge_chunk_endpoint(
    chunk_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeChunkRead:
    chunk = await knowledge_repository.set_status(session, chunk_id, "ACTIVE")
    if chunk is None:
        raise HTTPException(status_code=404, detail="knowledge chunk not found")
    return KnowledgeChunkRead.model_validate(chunk)
