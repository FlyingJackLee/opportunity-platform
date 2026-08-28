"""Lightweight DTOs for retrieval results -- fed into prompts and carried in
graph state, not DB models themselves."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IndustryKnowledgeItem(BaseModel):
    id: str
    title: str
    content: str
    topic: str | None = None


class DepartmentCandidateItem(BaseModel):
    id: str
    name: str
    responsibility: str | None = None
    topic_tags: list[str] = []


class OrganizationCandidateItem(BaseModel):
    id: str
    name: str
    region: str | None = None
    departments: list[DepartmentCandidateItem] = []


class CapabilityCandidateItem(BaseModel):
    id: str
    name: str
    scenarios: list[str] = []
    description: str | None = None


class KnowledgeChunkRead(BaseModel):
    """Admin-API read model -- unlike IndustryKnowledgeItem above (a
    retrieval-result DTO), this exposes the full row for CRUD. `embedding`
    is deliberately omitted -- it's server-computed (see
    app/knowledge/ingestion.py), never something a form edits directly."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_type: str
    title: str
    content: str
    industry: str | None
    region: str | None
    topic: str | None
    # ORM attribute is metadata_ (KnowledgeChunk.metadata_ maps to the DB
    # column "metadata", see app/models/knowledge.py); validation_alias reads
    # from that attribute name, but the JSON key stays "metadata" -- FastAPI
    # serializes response models by alias by default, so a plain `alias=`
    # here would leak "metadata_" into the API response.
    metadata: dict | None = Field(default=None, validation_alias="metadata_")
    status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkCreate(BaseModel):
    knowledge_type: str = "INDUSTRY"
    title: str
    content: str
    industry: str | None = None
    region: str | None = None
    topic: str | None = None
    metadata: dict | None = None
    status: str = "ACTIVE"


class KnowledgeChunkUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    industry: str | None = None
    region: str | None = None
    topic: str | None = None
    metadata: dict | None = None
