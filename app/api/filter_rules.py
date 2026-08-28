import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories import filter_rule_repository
from app.schemas.filter_rule import (
    EventFilterRuleCreate,
    EventFilterRuleRead,
    EventFilterRuleUpdate,
)

router = APIRouter(prefix="/api/v1/filter-rules", tags=["filter-rules"])


@router.get("", response_model=list[EventFilterRuleRead])
async def list_filter_rules_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[EventFilterRuleRead]:
    rules = await filter_rule_repository.list_all(session)
    return [EventFilterRuleRead.model_validate(r) for r in rules]


@router.post("", response_model=EventFilterRuleRead)
async def create_filter_rule_endpoint(
    payload: EventFilterRuleCreate,
    session: AsyncSession = Depends(get_session),
) -> EventFilterRuleRead:
    rule = await filter_rule_repository.create(session, **payload.model_dump())
    return EventFilterRuleRead.model_validate(rule)


@router.patch("/{rule_id}", response_model=EventFilterRuleRead)
async def update_filter_rule_endpoint(
    rule_id: uuid.UUID,
    payload: EventFilterRuleUpdate,
    session: AsyncSession = Depends(get_session),
) -> EventFilterRuleRead:
    rule = await filter_rule_repository.update(session, rule_id, **payload.model_dump())
    if rule is None:
        raise HTTPException(status_code=404, detail="filter rule not found")
    return EventFilterRuleRead.model_validate(rule)


@router.post("/{rule_id}/enable", response_model=EventFilterRuleRead)
async def enable_filter_rule_endpoint(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> EventFilterRuleRead:
    rule = await filter_rule_repository.set_enabled(session, rule_id, True)
    if rule is None:
        raise HTTPException(status_code=404, detail="filter rule not found")
    return EventFilterRuleRead.model_validate(rule)


@router.post("/{rule_id}/disable", response_model=EventFilterRuleRead)
async def disable_filter_rule_endpoint(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> EventFilterRuleRead:
    rule = await filter_rule_repository.set_enabled(session, rule_id, False)
    if rule is None:
        raise HTTPException(status_code=404, detail="filter rule not found")
    return EventFilterRuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_filter_rule_endpoint(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await filter_rule_repository.delete(session, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="filter rule not found")
