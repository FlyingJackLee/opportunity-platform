"""Lightweight DTOs for retrieval results -- fed into prompts and carried in
graph state, not DB models themselves."""

from pydantic import BaseModel


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
