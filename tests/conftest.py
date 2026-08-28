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
# ADR-0004: chat and embedding are independently selected. Without this, a
# real .env with EMBEDDING_PROVIDER=openai_compatible (needed for real
# development/testing) leaks into the test suite too -- app.state's real
# CompositeLLMGateway would then make live network calls to whatever
# embedding vendor is configured there, making the suite flaky/networked/
# credential-dependent instead of hermetic.
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")
# Same leak, same fix, but for delivery: app/main.py's build_delivery_channel
# picks the real DingTalkAdapter whenever settings.dingtalk_webhook_url is
# truthy, and falls through to the real .env value if nothing here sets it
# -- meaning every test run that exercises a push-eligible event (e.g.
# tests/test_events_api.py's full-pipeline test) was sending real messages
# to whatever DingTalk group .env points at. Force both webhook URLs empty
# (falsy) so tests always get RecordingDeliveryChannel, never a live send.
os.environ.setdefault("DINGTALK_WEBHOOK_URL", "")
os.environ.setdefault("DINGTALK_PUBLIC_GROUP_WEBHOOK_URL", "")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("APP_ENV", "test")
# Never let background cron jobs fire nondeterministically during the test
# suite -- collector tests call run_collection_cycle/POST /collectors/{id}/run
# directly instead.
os.environ.setdefault("COLLECTOR_SCHEDULER_ENABLED", "false")

import asyncio

import psycopg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings


async def _seed() -> None:
    from app.llm.providers.stub import StubLLMGateway
    from scripts.seed_phase2 import seed_all as seed_phase2_all
    from scripts.seed_phase3 import seed_all as seed_phase3_all

    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    gateway = StubLLMGateway(embedding_dimension=get_settings().embedding_dimension)
    async with session_factory() as session:
        await seed_phase2_all(session, gateway)
        await seed_phase3_all(session)
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    """Creates opportunity_platform_test if missing, runs `alembic upgrade
    head` against it (env.py reads the URL via get_settings(), which already
    resolves to the test DB thanks to the env vars set above), then seeds
    Phase 2's reference data once so every test has real rows to work
    against. asyncio.run() here (not a pytest_asyncio fixture) sidesteps a
    session-scoped-fixture/function-scoped-event-loop mismatch."""
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
    asyncio.run(_seed())


@pytest_asyncio.fixture
async def db_session():
    """Direct DB access for assertions -- independent of the app's own engine
    (built fresh per-app in main.py's lifespan). Truncates the per-run tables
    (`event`, `expert_run`, `push_record`) before each test for isolation --
    simpler than nested-transaction sharing given the app manages its own
    connection pool, separate from this fixture's. Reference data
    (organization/department/knowledge_chunk/capability/prompt_template/
    score_config/customer_owner/collector_source) is seeded once per session
    and left alone -- it's shared, static fixture data."""
    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(
            text(
                "TRUNCATE TABLE event, expert_run, push_record RESTART IDENTITY CASCADE"
            )
        )
    async with session_factory() as session:
        yield session
    await engine.dispose()
