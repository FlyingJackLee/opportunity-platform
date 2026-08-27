import uuid
from datetime import UTC, datetime

import pytest

from app.collector.dedup import find_duplicate
from app.models.event import (
    Event,
    EventStatus,
    compute_content_hash,
    compute_title_hash,
    compute_url_hash,
)


async def _seed_event(db_session, *, url: str, title: str, content: str) -> Event:
    event = Event(
        title=title,
        content=content,
        source_type="PUBLIC_WEB",
        source_url=url,
        status=EventStatus.NEW,
        collected_at=datetime.now(UTC),
        url_hash=compute_url_hash(url),
        title_hash=compute_title_hash(title),
        content_hash=compute_content_hash(content),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest.mark.usefixtures("_test_database")
async def test_exact_url_match_is_duplicate(db_session) -> None:
    seeded = await _seed_event(
        db_session, url="https://x.invalid/a", title="标题A", content="正文A"
    )

    duplicate = await find_duplicate(
        db_session, url="https://x.invalid/a", title="不同标题", content="不同正文"
    )

    assert duplicate is not None
    assert duplicate.id == seeded.id


@pytest.mark.usefixtures("_test_database")
async def test_same_title_different_url_is_duplicate(db_session) -> None:
    seeded = await _seed_event(
        db_session,
        url="https://x.invalid/a",
        title="城市生命线安全工程实施方案",
        content="正文A",
    )

    duplicate = await find_duplicate(
        db_session,
        url="https://y.invalid/republished",
        title="城市生命线安全工程实施方案",
        content="完全不同的正文",
    )

    assert duplicate is not None
    assert duplicate.id == seeded.id


@pytest.mark.usefixtures("_test_database")
async def test_same_content_different_title_and_url_is_duplicate(db_session) -> None:
    seeded = await _seed_event(
        db_session,
        url="https://x.invalid/a",
        title="标题A",
        content="完全相同的正文内容",
    )

    duplicate = await find_duplicate(
        db_session,
        url="https://z.invalid/b",
        title="完全不同的标题",
        content="完全相同的正文内容",
    )

    assert duplicate is not None
    assert duplicate.id == seeded.id


@pytest.mark.usefixtures("_test_database")
async def test_no_match_returns_none(db_session) -> None:
    await _seed_event(
        db_session, url="https://x.invalid/a", title="标题A", content="正文A"
    )

    duplicate = await find_duplicate(
        db_session,
        url=f"https://x.invalid/{uuid.uuid4()}",
        title="全新标题",
        content="全新正文",
    )

    assert duplicate is None
