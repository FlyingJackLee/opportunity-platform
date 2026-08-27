"""PostgreSQL-backed LangGraph checkpointer (spec §73) — used for run state,
fault recovery, future human-in-the-loop interrupts, and debugging.

`AsyncPostgresSaver.setup()` creates its own tables (checkpoints,
checkpoint_blobs, checkpoint_writes, checkpoint_migrations) via its own
internal versioning — independent of Alembic. This is langgraph-checkpoint-
postgres's own design, not something we chose; `setup_checkpointer` just calls
it (idempotent, safe on every startup)."""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import Settings


def checkpointer_context(settings: Settings):
    """Returns the (unentered) async context manager for an AsyncPostgresSaver.
    Must be held open for the lifetime of the app — see main.py's lifespan."""
    return AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url)


async def setup_checkpointer(checkpointer: AsyncPostgresSaver) -> None:
    await checkpointer.setup()
