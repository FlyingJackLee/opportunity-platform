from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embedding import embed_query
from app.llm.gateway import LLMGateway
from app.models.capability import Capability
from app.models.department import Department
from app.models.knowledge import KnowledgeChunk
from app.models.organization import Organization
from app.schemas.analysis import EventAnalysis
from app.schemas.knowledge import (
    CapabilityCandidateItem,
    DepartmentCandidateItem,
    IndustryKnowledgeItem,
    OrganizationCandidateItem,
)

INDUSTRY_TOP_K = 5
CAPABILITY_TOP_K = 5


def _query_text(event_analysis: EventAnalysis) -> str:
    """spec §38: query built from industry/topics/tasks/region."""
    parts = [
        *event_analysis.industry,
        *event_analysis.topics,
        *event_analysis.tasks,
        event_analysis.region,
    ]
    return " ".join(p for p in parts if p)


async def search_industry_knowledge(
    session: AsyncSession, gateway: LLMGateway, event_analysis: EventAnalysis
) -> list[IndustryKnowledgeItem]:
    query_vector = await embed_query(gateway, _query_text(event_analysis))
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.knowledge_type == "INDUSTRY")
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
        .limit(INDUSTRY_TOP_K)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        IndustryKnowledgeItem(
            id=str(row.id), title=row.title, content=row.content, topic=row.topic
        )
        for row in rows
    ]


async def search_organization_candidates(
    session: AsyncSession, event_analysis: EventAnalysis
) -> list[OrganizationCandidateItem]:
    """SQL-only, no vector search (spec §39/§104 principle 4: 结构化数据优先).
    Candidate filter is region match at the organization level; all
    departments of a matched organization become department candidates for
    expert_judge to reason over (topic_tags inform its judgment, not a
    pre-filter -- department counts per org are small at Phase 2 scale)."""
    org_stmt = select(Organization).where(
        Organization.region == event_analysis.region, Organization.status == "ACTIVE"
    )
    organizations = (await session.execute(org_stmt)).scalars().all()
    if not organizations:
        return []

    org_ids = [org.id for org in organizations]
    dept_stmt = select(Department).where(
        Department.organization_id.in_(org_ids), Department.status == "ACTIVE"
    )
    departments = (await session.execute(dept_stmt)).scalars().all()
    departments_by_org: dict = {}
    for dept in departments:
        departments_by_org.setdefault(dept.organization_id, []).append(
            DepartmentCandidateItem(
                id=str(dept.id),
                name=dept.name,
                responsibility=dept.responsibility,
                topic_tags=dept.topic_tags or [],
            )
        )

    return [
        OrganizationCandidateItem(
            id=str(org.id),
            name=org.name,
            region=org.region,
            departments=departments_by_org.get(org.id, []),
        )
        for org in organizations
    ]


async def search_capabilities(
    session: AsyncSession, gateway: LLMGateway, event_analysis: EventAnalysis
) -> list[CapabilityCandidateItem]:
    query_vector = await embed_query(gateway, _query_text(event_analysis))
    stmt = (
        select(Capability)
        .where(Capability.status == "ACTIVE")
        .order_by(Capability.embedding.cosine_distance(query_vector))
        .limit(CAPABILITY_TOP_K)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        CapabilityCandidateItem(
            id=str(row.id),
            name=row.name,
            scenarios=row.scenarios or [],
            description=row.description,
        )
        for row in rows
    ]
