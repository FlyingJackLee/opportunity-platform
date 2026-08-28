"""Controlled vocabulary for `region`/`industry` tags (CONTEXT.md: "Industry / Region Tag").

DB columns stay plain VARCHAR (see app/models/event.py) so adding a new tag never
requires an ALTER TYPE migration; membership is enforced at the Pydantic schema
boundary instead (see app/schemas/event.py). Extend these enums as new
industries/regions are onboarded during trial runs (spec §101/§102).
"""

from enum import StrEnum


class Industry(StrEnum):
    ZHUJIAN = "住建"
    FAGAI = "发改"
    JINGXIN = "经信"
    SHUJU = "数据"
    GUOZI = "国资"


class Region(StrEnum):
    CHONGQING = "重庆市"


class SourceType(StrEnum):
    """collector_source.source_type -- spec §9's site-category vocabulary
    (only ever gives GOV_WEB/招标网站 as examples, never an exhaustive list;
    this set is inferred, not spec-literal, same caveat as EventType in
    app/schemas/analysis.py). Currently descriptive only -- no node branches
    on it (app/collector/parser_type is what's actually enum-enforced, via
    PARSER_REGISTRY)."""

    GOV_WEB = "GOV_WEB"
    TENDER_SITE = "TENDER_SITE"
    NEWS_SITE = "NEWS_SITE"
    OTHER = "OTHER"


class OrganizationType(StrEnum):
    """organization.organization_type -- not given any example values in
    spec at all; this set is inferred. Descriptive only, like SourceType --
    no retrieval/scoring logic branches on it (see
    app/knowledge/retriever.py's search_organization_candidates, which
    filters candidates by region only)."""

    GOV = "GOV"
    SOE = "SOE"
    INSTITUTION = "INSTITUTION"
    OTHER = "OTHER"
