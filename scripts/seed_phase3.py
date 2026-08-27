"""Phase 3 seed data. Does NOT invent a fictitious real government source --
seeds exactly one disabled placeholder collector_source, commented for the
operator to duplicate with a real list_url/schedule/tags once sources are
identified (no code change needed at that point). The end-to-end test does
not depend on this row -- it inserts its own collector_source pointed at
whatever ephemeral port its local fixture HTTP server actually bound to.

Run after `alembic upgrade head`:

    uv run python scripts/seed_phase3.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import make_engine, make_session_factory
from app.core.ids import seed_uuid
from app.models.collector_source import CollectorSource

PLACEHOLDER_SOURCE_KEY = "collector_source:placeholder-template"


async def seed_all(session: AsyncSession) -> None:
    await session.merge(
        CollectorSource(
            id=seed_uuid(PLACEHOLDER_SOURCE_KEY),
            name="[模板-未启用] 复制这行并改成真实信息源",
            source_type="GOV_WEB",
            base_url="https://example.invalid",
            list_url="https://example.invalid/list",
            enabled=False,
            schedule="0 */2 * * *",
            parser_type="GOV_GENERIC",
            industry_tags=["住建"],
            region_tags=["重庆市"],
            priority=0,
        )
    )
    await session.commit()


async def main() -> None:
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    async with session_factory() as session:
        await seed_all(session)
    await engine.dispose()
    print("phase 3 seed data ready")


if __name__ == "__main__":
    asyncio.run(main())
