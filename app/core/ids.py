"""Deterministic UUIDs for seed data and stub-gateway fixtures. Both
scripts/seed_phase2.py and app/llm/providers/fixtures.py call seed_uuid with
the same natural keys, so fixture-referenced department_id/organization_id
values line up with real seeded rows without any runtime coupling."""

import uuid

_NAMESPACE = uuid.UUID("6f6b0f3a-3b7e-4c8e-9f2a-2d6a2b6a6b6a")


def seed_uuid(natural_key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, natural_key)
