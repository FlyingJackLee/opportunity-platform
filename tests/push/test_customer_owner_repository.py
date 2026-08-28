import pytest

from app.core.ids import seed_uuid
from app.core.seed_keys import (
    DEPT_CHENGJIAN_CHU,
    DEPT_KEJI_XINXI_CHU,
    ORG_FAGAI_WEI,
    ORG_ZHUJIAN_WEI,
)
from app.models.push_record import RecipientType
from app.repositories.customer_owner_repository import resolve_owner


@pytest.mark.usefixtures("_test_database")
async def test_department_owner_hit(db_session) -> None:
    """科技信息处 has its own department-level owner (李四) -- spec §61's
    "specific owner exists" branch."""
    match = await resolve_owner(
        db_session,
        organization_id=str(seed_uuid(ORG_ZHUJIAN_WEI)),
        department_id=str(seed_uuid(DEPT_KEJI_XINXI_CHU)),
    )
    assert match is not None
    assert match.recipient_type == RecipientType.DEPARTMENT_OWNER
    assert match.owner.owner_name == "李四"


@pytest.mark.usefixtures("_test_database")
async def test_falls_back_to_organization_owner(db_session) -> None:
    """城建处 has no department-level owner -- spec §61's exact worked
    example: falls back to the organization-level owner (张三)."""
    match = await resolve_owner(
        db_session,
        organization_id=str(seed_uuid(ORG_ZHUJIAN_WEI)),
        department_id=str(seed_uuid(DEPT_CHENGJIAN_CHU)),
    )
    assert match is not None
    assert match.recipient_type == RecipientType.ORGANIZATION_OWNER
    assert match.owner.owner_name == "张三"


@pytest.mark.usefixtures("_test_database")
async def test_no_owner_anywhere_returns_none(db_session) -> None:
    """ORG_FAGAI_WEI deliberately has no Customer Owner configured at all."""
    match = await resolve_owner(
        db_session,
        organization_id=str(seed_uuid(ORG_FAGAI_WEI)),
        department_id="UNKNOWN",
    )
    assert match is None


@pytest.mark.usefixtures("_test_database")
async def test_unknown_sentinel_does_not_raise(db_session) -> None:
    match = await resolve_owner(
        db_session, organization_id="UNKNOWN", department_id="UNKNOWN"
    )
    assert match is None


@pytest.mark.usefixtures("_test_database")
async def test_unparseable_ids_do_not_raise(db_session) -> None:
    match = await resolve_owner(
        db_session, organization_id="not-a-uuid", department_id="also-not"
    )
    assert match is None
