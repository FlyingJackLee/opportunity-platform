"""Test env vars must be set before anything imports app.core.config.get_settings
(it's @lru_cache'd, first call wins) -- conftest.py is always imported before
test collection in this directory, so setting them at module level here is
safe as long as nothing else imports app.main first.
"""

import os
from pathlib import Path

TEST_DB_NAME = "opportunity_platform_test"
ADMIN_DB_URL = (
    "postgresql://opportunity:opportunity@localhost:55432/opportunity_platform"
)
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://opportunity:opportunity@localhost:55432/{TEST_DB_NAME}"
)
TEST_CHECKPOINT_DATABASE_URL = (
    f"postgresql://opportunity:opportunity@localhost:55432/{TEST_DB_NAME}"
)

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("CHECKPOINT_DATABASE_URL", TEST_CHECKPOINT_DATABASE_URL)
os.environ.setdefault("LLM_PROVIDER", "stub")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("APP_ENV", "test")

import psycopg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    """Creates opportunity_platform_test if missing, then runs `alembic upgrade
    head` against it (env.py reads the URL via get_settings(), which already
    resolves to the test DB thanks to the env vars set above)."""
    conn = psycopg.connect(ADMIN_DB_URL, autocommit=True)
    try:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        conn.close()

    repo_root = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(repo_root / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session():
    """Direct DB access for assertions -- independent of the app's own engine
    (built fresh per-app in main.py's lifespan). Truncates `event` before each
    test for isolation (simpler than nested-transaction sharing given the app
    manages its own connection pool, separate from this fixture's)."""
    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("TRUNCATE TABLE event RESTART IDENTITY CASCADE"))
    async with session_factory() as session:
        yield session
    await engine.dispose()
